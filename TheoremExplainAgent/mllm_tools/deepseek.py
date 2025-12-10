from typing import List, Dict, Any, Union, Optional
import os
import base64
import mimetypes
from openai import OpenAI
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()
class DeepSeekWrapper:
    """Wrapper for DeepSeek API (via OpenAI SDK compatibility)"""
    
    def __init__(
        self,
        model_name: str = "deepseek-reasoner",
        temperature: float = 1.0, # DeepSeek often recommends higher temp (1.0-1.3) for V3/Coder
        verbose: bool = False,
        base_url: str = "https://api.deepseek.com/v3.2_speciale_expires_on_20251215",
    ):
        """
        Initialize the DeepSeek wrapper
        
        Args:
            model_name: The model ID (e.g. "deepseek-chat" or your specific "DeepSeek-V3.2-Speciale")
            temperature: Temperature for completion
            verbose: Whether to print verbose output
            base_url: DeepSeek API Endpoint
        """
        self.model_name = model_name
        self.temperature = temperature
        self.verbose = verbose
        
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("No API_KEY found. Please set the `DEEPSEEK_API_KEY` environment variable.")
            
        # DeepSeek is OpenAI-compatible
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def _encode_file(self, file_path: Union[str, Image.Image]) -> str:
        """Encode local file or PIL Image to base64 string"""
        if isinstance(file_path, Image.Image):
            buffered = io.BytesIO()
            file_path.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        else:
            with open(file_path, "rb") as file:
                return base64.b64encode(file.read()).decode("utf-8")

    def _get_mime_type(self, file_path: str) -> str:
        """Get the MIME type of a file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "image/png"

    def __call__(self, messages: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Process messages and return completion
        """
        formatted_messages = []
        
        # DeepSeek System Prompt for context (Optional, but good practice)
        # formatted_messages.append({"role": "system", "content": "You are a helpful assistant."})

        for msg in messages:
            if msg["type"] == "text":
                formatted_messages.append({
                    "role": "user",
                    "content": msg["content"]
                })
            
            # Handling Images (Assuming OpenAI-compatible Vision format for this Speciale model)
            elif msg["type"] == "image":
                try:
                    # 1. Handle encoding
                    if isinstance(msg["content"], (Image.Image, str)) and os.path.exists(msg["content"] if isinstance(msg["content"], str) else ""):
                         base64_image = self._encode_file(msg["content"])
                         data_url = f"data:image/png;base64,{base64_image}"
                    else:
                        # Assume it's already a URL
                        data_url = msg["content"]

                    # 2. Format for API
                    formatted_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url
                                }
                            }
                        ]
                    })
                except Exception as e:
                    print(f"Warning: Could not process image for DeepSeek: {e}")
                    continue
            else:
                # Fallback for audio/video if strictly text model, or ignore
                pass

        try:
            if self.verbose:
                print(f"Sending request to {self.model_name}...")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_messages,
                temperature=self.temperature,
                stream=False
            )

            # DeepSeek specific: Check usage if verbose
            if self.verbose and response.usage:
                print(f"Token Usage - Prompt: {response.usage.prompt_tokens}, Completion: {response.usage.completion_tokens}")

            return response.choices[0].message.content

        except Exception as e:
            print(f"Error in DeepSeek completion: {e}")
            return str(e)

if __name__ == "__main__":
    # Test block
    wrapper = DeepSeekWrapper(verbose=True)
    response = wrapper([{"type": "text", "content": "Hello, are you the Speciale version?"}])
    print(response)
    pass