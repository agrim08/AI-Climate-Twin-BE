# 1. Disable permission inheritance and remove other users
icacls.exe "C:\path\to\aws_climate_twin.pem" /inheritance:r

# 2. Grant explicit Read access ONLY to your current Windows user account
icacls.exe "C:\path\to\aws_climate_twin.pem" /grant:r "$($env:USERNAME):R"


# Run the SSH Command
Open PowerShell (or Command Prompt) and run:

cmd
ssh -i "C:\path\to\aws_climate_twin.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>