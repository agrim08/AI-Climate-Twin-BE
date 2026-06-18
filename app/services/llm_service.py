import os
import sys
import json
import logging
from typing import Optional, Dict, Any, List

# Add the project root directory to sys.path to support direct script execution
# without triggering app.services.__init__.py package imports (bypassing sqlalchemy/pandas).
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add services directory to sys.path to support direct import of gemini_service
services_dir = os.path.dirname(os.path.abspath(__file__))
if services_dir not in sys.path:
    sys.path.insert(0, services_dir)

if __name__ == "__main__":
    from gemini_service import GeminiService
else:
    from app.services.gemini_service import GeminiService

logger = logging.getLogger("app.chatbot")

class LLMService:
    """Service to load crop requirements and suggest suitable crops based on climate data, with Gemini AI enrichment."""

    def __init__(self):
        """Initializes the service, loads crop data, and connects the Gemini AI client."""
        # Resolve the crops.json file path relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.crops_file_path = os.path.join(current_dir, "..", "data", "crops.json")
        self.crop_data = self.load_crop_data()

        # Initialize the Gemini service
        self.gemini_service = GeminiService()

    def load_crop_data(self):
        """Loads crop data from crops.json and returns it as a dictionary."""
        if not os.path.exists(self.crops_file_path):
            raise FileNotFoundError(f"crops.json not found at {self.crops_file_path}")
        with open(self.crops_file_path, "r") as file:
            return json.load(file)

    def get_suitable_crops(self, temperature, rainfall):
        """Returns a list of crops suitable for the given temperature and rainfall."""
        suitable_crops = []
        for crop_name, reqs in self.crop_data.items():
            temp_matches = reqs["min_temp"] <= temperature <= reqs["max_temp"]
            rainfall_matches = reqs["min_rainfall"] <= rainfall <= reqs["max_rainfall"]
            if temp_matches and rainfall_matches:
                suitable_crops.append(crop_name)
        return suitable_crops

    def can_grow_crop(self, crop_name, temperature, rainfall):
        """Checks if a specific crop can be grown in the given temperature and rainfall conditions."""
        # Support case-insensitive matching by searching for the crop in self.crop_data
        matched_crop_name = None
        for key in self.crop_data:
            if key.lower() == crop_name.lower():
                matched_crop_name = key
                break

        if not matched_crop_name:
            return {
                "found": False,
                "message": "Crop not found."
            }

        requirements = self.crop_data[matched_crop_name]
        min_temp = requirements["min_temp"]
        max_temp = requirements["max_temp"]
        min_rainfall = requirements["min_rainfall"]
        max_rainfall = requirements["max_rainfall"]

        temp_ok = min_temp <= temperature <= max_temp
        rainfall_ok = min_rainfall <= rainfall <= max_rainfall

        if temp_ok and rainfall_ok:
            return {
                "found": True,
                "crop": matched_crop_name,
                "suitable": True,
                "reason": "Temperature and rainfall are within acceptable limits."
            }
        else:
            # Construct a detailed explanation of why it failed
            reasons = []
            if not temp_ok:
                if temperature < min_temp:
                    reasons.append("temperature is below required range")
                else:
                    reasons.append("temperature is above required range")
            if not rainfall_ok:
                if rainfall < min_rainfall:
                    reasons.append("rainfall is below required range")
                else:
                    reasons.append("rainfall is above required range")

            reason_str = " and ".join(reasons) + "."
            # Capitalize the first letter for consistency with standard reason sentences
            reason_str = reason_str[0].upper() + reason_str[1:]

            return {
                "found": True,
                "crop": matched_crop_name,
                "suitable": False,
                "reason": reason_str
            }

    def generate_climate_report(self, temperature, rainfall, drought_risk):
        """Generates a formatted climate summary report with crop recommendations."""
        suitable_crops = self.get_suitable_crops(temperature, rainfall)

        # Format crops list with hyphens as in example
        if suitable_crops:
            crops_list = "\n".join(f"- {crop}" for crop in suitable_crops)
        else:
            crops_list = "- No suitable crops found"

        # Determine recommendations based on conditions
        if str(drought_risk).lower() == "high":
            recommendation = "Drought risk is High. Focus on cultivating drought-resistant crops like Bajra or Jowar, and utilize water conservation methods like drip irrigation."
        elif rainfall < 500:
            recommendation = "Low rainfall conditions. Supplemental irrigation is advised. Consider soil mulching to conserve moisture."
        elif rainfall > 1500:
            recommendation = "High rainfall conditions. Ensure proper field drainage to avoid waterlogging, and focus on water-loving crops like Rice."
        else:
            recommendation = "Climate conditions are moderate."

        # Compile clean formatted report
        report = (
            f"Climate Summary\n\n"
            f"Temperature: {temperature}°C\n"
            f"Rainfall: {rainfall} mm\n"
            f"Drought Risk: {drought_risk}\n\n"
            f"Suitable Crops:\n\n"
            f"{crops_list}\n\n"
            f"Recommendations:\n\n"
            f"{recommendation}"
        )
        return report

    def answer_user_question(
        self,
        question: str,
        temperature: float,
        rainfall: float,
        drought_risk: str,
        extra_context: Optional[Dict[str, Any]] = None
    ):
        """
        Processes a natural language user query.
        Performs rule-based logic first to generate structured values and contexts,
        queries the Gemini AI service for a detailed natural response, and falls back to
        rule-based text if the Gemini API call fails.
        """
        question_lower = question.lower()
        rule_based_response = None
        prompt = None

        # Build suitable crops cache for context
        suitable_crops = self.get_suitable_crops(temperature, rainfall)

        # 1. Route query to appropriate prompt templates or rule outputs
        if "what crops" in question_lower or "suitable crops" in question_lower:
            # For list of suitable crops, return the raw list directly as in requirements
            return suitable_crops

        elif "can i grow" in question_lower:
            # Extract crop name following "can i grow"
            start_idx = question_lower.find("can i grow") + len("can i grow")
            crop_name_raw = question[start_idx:].strip("? \t\n\r.")
            
            # Match crop name against database
            crop_to_check = None
            for key in self.crop_data:
                if key.lower() in crop_name_raw.lower():
                    crop_to_check = key
                    break
            if not crop_to_check:
                crop_to_check = crop_name_raw

            res = self.can_grow_crop(crop_to_check, temperature, rainfall)
            if not res["found"]:
                return res["message"]

            # Format the default rule-based response
            if res["suitable"]:
                rule_based_response = f"{res['crop']} is suitable. {res['reason']}"
            else:
                reason = res["reason"].strip(".")
                if reason and reason[0].isupper():
                    reason = reason[0].lower() + reason[1:]
                rule_based_response = f"{res['crop']} is not suitable because {reason}."

            # Generate Gemini Prompt
            if self.gemini_service.is_available():
                prompt = self.gemini_service.get_crop_suitability_prompt(
                    crop_name=res["crop"],
                    temp=temperature,
                    rainfall=rainfall,
                    rule_reason=res["reason"]
                )

        elif "climate report" in question_lower:
            # Generate the default rule-based climate report
            rule_based_response = self.generate_climate_report(temperature, rainfall, drought_risk)

            # Extract rule-based recommendation for the template
            if str(drought_risk).lower() == "high":
                recommendation_rule = "Drought risk is High. Focus on cultivating drought-resistant crops like Bajra or Jowar, and utilize water conservation methods like drip irrigation."
            elif rainfall < 500:
                recommendation_rule = "Low rainfall conditions. Supplemental irrigation is advised. Consider soil mulching to conserve moisture."
            elif rainfall > 1500:
                recommendation_rule = "High rainfall conditions. Ensure proper field drainage to avoid waterlogging, and focus on water-loving crops like Rice."
            else:
                recommendation_rule = "Climate conditions are moderate."

            # Generate Gemini Prompt
            if self.gemini_service.is_available():
                prompt = self.gemini_service.get_climate_report_prompt(
                    temp=temperature,
                    rainfall=rainfall,
                    drought_risk=drought_risk,
                    suitable_crops=suitable_crops,
                    recommendations_rule=recommendation_rule
                )

        else:
            # Check for general recommendations or scenario queries in the text
            rule_based_response = "Sorry, I can currently answer crop suitability and climate report questions."

            if self.gemini_service.is_available():
                if "recommend" in question_lower or "advice" in question_lower:
                    prompt = self.gemini_service.get_farmer_recommendations_prompt(
                        temp=temperature,
                        rainfall=rainfall,
                        drought_risk=drought_risk,
                        suitable_crops=suitable_crops
                    )
                elif "scenario" in question_lower or "what if" in question_lower:
                    prompt = self.gemini_service.get_climate_scenario_prompt(
                        temp=temperature,
                        rainfall=rainfall,
                        scenario_shift=question
                    )

        # 2. Inject extra context if provided (for future forecasts/simulations integration)
        if prompt and extra_context:
            context_addition = "\n\nAdditional Extended Context (Forecast/Simulation data):\n"
            for key, val in extra_context.items():
                context_addition += f"- {key}: {val}\n"
            prompt += context_addition

        # 3. Call Gemini if available, with robust fallback handling
        if prompt and self.gemini_service.is_available():
            try:
                logger.info("Sending query prompt to Gemini service...")
                gemini_answer = self.gemini_service.generate_response(prompt)
                logger.info("Gemini response retrieved successfully.")
                return gemini_answer
            except Exception as e:
                logger.warning(
                    "Gemini query failed. Falling back to rule-based response. Error: %s",
                    str(e)
                )
                return rule_based_response

        # Fallback to rule-based response if no prompt was built or Gemini service is unavailable
        return rule_based_response

if __name__ == "__main__":
    service = LLMService()
    
    # Define test climate inputs
    test_temp = 22
    test_rainfall = 600
    test_drought_risk = "Low"
    
    print("--- Running Test Cases ---")
    print()

    # 1. Suitable crops
    print("Test Case 1: Suitable Crops")
    q1 = "What crops can I grow in this area?"
    print(f"Question: '{q1}'")
    print(f"Output: {service.answer_user_question(q1, test_temp, test_rainfall, test_drought_risk)}")
    print()

    # 2. Climate report
    print("Test Case 2: Climate Report")
    q2 = "Could you give me a climate report?"
    print(f"Question: '{q2}'")
    print("Output:")
    print(service.answer_user_question(q2, test_temp, test_rainfall, test_drought_risk))
    print()

    # 3. Can I grow Rice?
    print("Test Case 3: Can I grow Rice?")
    q3 = "Can I grow Rice?"
    print(f"Question: '{q3}'")
    print(f"Output: {service.answer_user_question(q3, test_temp, test_rainfall, test_drought_risk)}")
    print()

    # 4. Can I grow Wheat?
    print("Test Case 4: Can I grow Wheat?")
    q4 = "Can I grow Wheat?"
    print(f"Question: '{q4}'")
    print(f"Output: {service.answer_user_question(q4, test_temp, test_rainfall, test_drought_risk)}")
    print()

    # 5. Unsupported question
    print("Test Case 5: Unsupported Question")
    q5 = "What is the capital of India?"
    print(f"Question: '{q5}'")
    print(f"Output: {service.answer_user_question(q5, test_temp, test_rainfall, test_drought_risk)}")
