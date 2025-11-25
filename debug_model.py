import os
from openai import OpenAI

def test_model():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        return

    client = OpenAI(api_key=api_key)
    model = "gpt-4o"
    
    print(f"Testing connection with model: {model}...")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("Success! Model is working.")
        print("Response:", response.choices[0].message.content)
    except Exception as e:
        print("\nFAILED to use model.")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")

if __name__ == "__main__":
    test_model()
