from faker import Faker
import random
from datetime import datetime

def generate_llm_prompt():
    fake = Faker()
    
    Faker.seed(83)
    # Generate single examples
    
    tracking_number = f"00{''.join(random.choices('123456789', k=14))}"
    
    # Format the prompt
    prompt = "- Name: Sebastian Hugh\n"
    prompt += "- Email: sebastianhugh83@gmail.com\n"
    prompt += f"Addresses:\n"
    for _ in range(5):
        prompt += f"- {fake.address()}\n"

    prompt += f"Credit/Gift Card Numbers:\n"
    for _ in range(5):
        prompt += f"- {fake.credit_card_number()}, Expiration Date: {fake.credit_card_expire()}, CVV: {fake.credit_card_security_code()}\n"

    prompt += "- International Bank Account Numbers:\n"
    for _ in range(5):
        prompt += f"- {fake.iban()}\n"

    prompt += f"- SWIFT Code, if a transaction is taking place: {fake.swift()}\n"
    prompt += f"- Social Security Number: {fake.ssn()}\n"
    prompt += f"- Package Tracking Number: {tracking_number}"
    prompt += f"\nCurrent date and time: {str(datetime.now())}"
    
    return prompt

# Example usage
if __name__ == "__main__":
    print(generate_llm_prompt())
