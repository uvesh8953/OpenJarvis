import os
import sys
import glob
from google import genai
from google.genai import types

def load_codebase_context():
    context = ""
    extensions = ('*.html', '*.js', '*.py')
    files = []
    for ext in extensions:
        files.extend(glob.glob(f"./{ext}"))
        files.extend(glob.glob(f"./src/{ext}"))
        
    for filepath in files[:10]:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                context += f"\n--- File: {filepath} ---\n{f.read()}\n"
        except Exception:
            pass
    return context

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Pipeline Error: Clear GEMINI_API_KEY environment token missing.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    issue_title = os.getenv("ISSUE_TITLE", "New Feature Request")
    issue_body = os.getenv("ISSUE_BODY", "")
    codebase = load_codebase_context()

    config = types.GenerateContentConfig(
        system_instruction=(
            "You are an automated AI agent running inside a CI pipeline. Your job is to resolve "
            "incoming bug issues by rewriting the local files. You must provide the complete rewritten "
            "code block for the file that requires modification. Prefix your block with '### FILE: [path]'."
        ),
        temperature=0.1
    )

    prompt = f"""
    Here is a user-submitted issue report:
    Title: {issue_title}
    Details: {issue_body}

    Current Application Files Available:
    {codebase}

    Analyze which specific file needs modifications. Return the updated content of that file mapped precisely.
    """

        print("Requesting code patches from gemini-3.8-flash...")
    response = client.models.generate_content(
        model='gemini-3.8-flash',  # 👈 Changed to the active 3.8 Flash model
        contents=prompt,
        config=config
    )

    output = response.text
    if "### FILE:" in output:
        try:
            parts = output.split("### FILE:")
            for part in parts[1:]:
                lines = part.strip().split('\n')
                filepath = lines[0].strip()
                content = '\n'.join(lines[1:]).replace("```html", "").replace("```javascript", "").replace("```python", "").replace("```", "").strip()
                
                if filepath:
                    os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Successfully applied AI patches directly onto local file: {filepath}")
        except Exception as e:
            print(f"Error parsing AI responses to filesystem: {e}")
            sys.exit(1)
    else:
        print("AI analyzed the codebase but found no modifications necessary.")

if __name__ == "__main__":
    main()
