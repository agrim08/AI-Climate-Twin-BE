import os
import json

class LLMService:
    """Service to load crop requirements and suggest suitable crops based on climate data."""

    def __init__(self):
        # Resolve the crops.json file path relative to this script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.crops_file_path = os.path.join(current_dir, "..", "data", "crops.json")
        self.crop_data = self.load_crop_data()

    def load_crop_data(self):
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

    def generate_climate_report(self, temperature, rainfall, drought_risk):
        """Generates a human-readable climate report with crop recommendations."""
        # Step 1: Call get_suitable_crops internally to find matching crops
        suitable_crops = self.get_suitable_crops(temperature, rainfall)

        # Step 2: Format the list of suitable crops as a bulleted list
        # If crops are found, prefix each with an asterisk; otherwise state none were found
        if suitable_crops:
            crops_list = "\n".join(f"* {crop}" for crop in suitable_crops)
        else:
            crops_list = "* No suitable crops found"

        # Step 3: Determine recommendations based on the climate conditions
        # We check the level of drought risk first
        if str(drought_risk).lower() == "high":
            recommendation = "Drought risk is High. Focus on cultivating drought-resistant crops like Bajra or Jowar, and utilize water conservation methods like drip irrigation."
        # If rainfall is low, suggest additional irrigation
        elif rainfall < 500:
            recommendation = "Low rainfall conditions. Supplemental irrigation is advised. Consider soil mulching to conserve moisture."
        # If rainfall is very high, suggest drainage management
        elif rainfall > 1500:
            recommendation = "High rainfall conditions. Ensure proper field drainage to avoid waterlogging, and focus on water-loving crops like Rice."
        # Otherwise, provide a standard recommendation
        else:
            recommendation = "Climate conditions are moderate. Proceed with standard crop planning and maintain balanced soil health."

        # Step 4: Build the formatted markdown report string
        report = (
            f"## Climate Summary\n\n"
            f"Temperature: {temperature}°C\n"
            f"Rainfall: {rainfall} mm\n"
            f"Drought Risk: {drought_risk}\n\n"
            f"Suitable Crops:\n\n"
            f"{crops_list}\n\n"
            f"Recommendations:\n"
            f"{recommendation}"
        )

        # Step 5: Return the compiled report string
        return report

    def can_grow_crop(self, crop_name, temperature, rainfall):
        """Checks if a specific crop can be grown in the given temperature and rainfall conditions."""
        # Step 1: Search for the crop inside crop_data using standard case-sensitive lookup
        # If the crop does not exist in our dataset, return a failure dictionary
        if crop_name not in self.crop_data:
            return {
                "found": False,
                "message": "Crop not found"
            }
        
        # Step 2: Retrieve the crop requirements if it exists
        requirements = self.crop_data[crop_name]
        min_temp = requirements["min_temp"]
        max_temp = requirements["max_temp"]
        min_rainfall = requirements["min_rainfall"]
        max_rainfall = requirements["max_rainfall"]
        
        # Step 3: Check temperature and rainfall ranges
        temp_ok = min_temp <= temperature <= max_temp
        rainfall_ok = min_rainfall <= rainfall <= max_rainfall
        
        # Step 4: Build explanations of why the crop is or is not suitable
        reasons = []
        if not temp_ok:
            if temperature < min_temp:
                reasons.append(f"temperature is too low ({temperature}°C, required: {min_temp}°C to {max_temp}°C)")
            else:
                reasons.append(f"temperature is too high ({temperature}°C, required: {min_temp}°C to {max_temp}°C)")
                
        if not rainfall_ok:
            if rainfall < min_rainfall:
                reasons.append(f"rainfall is too low ({rainfall} mm, required: {min_rainfall} mm to {max_rainfall} mm)")
            else:
                reasons.append(f"rainfall is too high ({rainfall} mm, required: {min_rainfall} mm to {max_rainfall} mm)")
        
        # Step 5: Compile suitability status and detailed reasons into the final return dictionary
        if temp_ok and rainfall_ok:
            return {
                "found": True,
                "crop": crop_name,
                "suitable": True,
                "reason": f"The climate is suitable. Both temperature ({temperature}°C) and rainfall ({rainfall} mm) are within required bounds of {min_temp}-{max_temp}°C and {min_rainfall}-{max_rainfall} mm respectively."
            }
        else:
            detailed_reason = "The climate is not suitable because " + " and ".join(reasons) + "."
            return {
                "found": True,
                "crop": crop_name,
                "suitable": False,
                "reason": detailed_reason
            }

    def answer_user_question(self, question, temperature, rainfall, drought_risk):
        """Processes a natural language query and routes it to the appropriate class methods."""
        # Step 1: Convert the input question to lowercase to ensure case-insensitive matching
        question_lower = question.lower()

        # Step 2: Check if the question asks for suitable crops or what crops can be grown
        if "what crops" in question_lower or "suitable crops" in question_lower:
            # Call get_suitable_crops and return the matching crops list directly
            return self.get_suitable_crops(temperature, rainfall)

        # Step 3: Check if the question asks about growing a specific crop (e.g. "Can I grow ...")
        elif "can i grow" in question_lower:
            # Initialize a variable to track the crop name we want to check
            crop_to_check = None
            
            # Look for a case-insensitive match from our known crops list in the question string
            for crop_name in self.crop_data:
                if crop_name.lower() in question_lower:
                    crop_to_check = crop_name
                    break
            
            # If no known crop in our database was found, extract whatever text follows "can i grow"
            if not crop_to_check:
                # Find the starting index of the phrase "can i grow" and add its length (10 characters)
                start_index = question_lower.find("can i grow") + 10
                # Extract the trailing crop name, stripping punctuation marks and whitespace
                raw_crop_name = question[start_index:].strip("? \t\n\r.")
                # Capitalize the first letter (Title Case) to match crops keys
                crop_to_check = raw_crop_name.title()

            # Call can_grow_crop with the extracted crop name and return its dictionary result
            return self.can_grow_crop(crop_to_check, temperature, rainfall)

        # Step 4: Check if the question asks for a climate report
        elif "climate report" in question_lower:
            # Call generate_climate_report and return the formatted report string
            return self.generate_climate_report(temperature, rainfall, drought_risk)

        # Step 5: For all other queries, return a standard helpful error message
        else:
            return "Sorry, I can currently answer crop suitability and climate report questions."

if __name__ == "__main__":
    service = LLMService()
    
    # Define test climate inputs
    test_temp = 22
    test_rainfall = 600
    test_drought_risk = "Low"
    
    print("--- Testing answer_user_question() Method ---")
    print()

    # Test case 1: Question about suitable crops
    q1 = "What crops can I grow in this area?"
    print(f"Question: '{q1}'")
    print(f"Answer: {service.answer_user_question(q1, test_temp, test_rainfall, test_drought_risk)}")
    print("-" * 50)

    # Test case 2: Question about a specific suitable crop (Wheat)
    q2 = "Can I grow wheat?"
    print(f"Question: '{q2}'")
    print(f"Answer: {service.answer_user_question(q2, test_temp, test_rainfall, test_drought_risk)}")
    print("-" * 50)

    # Test case 3: Question about a specific unsuitable crop (Rice)
    q3 = "Can I grow rice?"
    print(f"Question: '{q3}'")
    print(f"Answer: {service.answer_user_question(q3, test_temp, test_rainfall, test_drought_risk)}")
    print("-" * 50)

    # Test case 4: Question about a crop that doesn't exist
    q4 = "Can I grow apples?"
    print(f"Question: '{q4}'")
    print(f"Answer: {service.answer_user_question(q4, test_temp, test_rainfall, test_drought_risk)}")
    print("-" * 50)

    # Test case 5: Question asking for a climate report
    q5 = "Could you give me a climate report?"
    print(f"Question: '{q5}'")
    print("Answer:")
    print(service.answer_user_question(q5, test_temp, test_rainfall, test_drought_risk))
    print("-" * 50)

    # Test case 6: Unrelated question
    q6 = "What is the capital of India?"
    print(f"Question: '{q6}'")
    print(f"Answer: {service.answer_user_question(q6, test_temp, test_rainfall, test_drought_risk)}")
    print("-" * 50)
