from starknet_py.net.account.account import Account
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.contract import Contract
import json
import requests
import re
from typing import List, Dict, Any

class NPCContract:
    def __init__(self, node_url, private_key, account_address, contract_address):
        self.client = FullNodeClient(node_url=node_url)
        self.private_key = private_key
        self.account_address = account_address
        self.contract_address = contract_address

    def _get_account(self):
        return Account(
            client=self.client,
            address=self.account_address,
            key_pair=KeyPair.from_private_key(self.private_key),
            chain=0x4b4154414e41,  # Chain ID for Katana local node
        )

    async def get_mood(self):
        account = self._get_account()
        contract = await Contract.from_address(self.contract_address, account)
        mood = await contract.functions["get_mood"].call()
        mood_int = mood[0]
        return mood_int.to_bytes((mood_int.bit_length() + 7) // 8, 'big').decode('ascii')

    async def change_mood(self, new_mood):
        print(f"Changing mood to: {new_mood}")
        account = self._get_account()
        contract = await Contract.from_address(self.contract_address, account)
        mood_bytes = new_mood.encode('ascii')
        mood_int = int.from_bytes(mood_bytes, 'big')
        print(f"Calling change_mood with mood_int: {mood_int}")
        try:
            invocation = await contract.functions["change_mood"].invoke_v1(mood_int, max_fee=int(1e16))
            print(f"Invocation successful: {invocation}")
            
            # Check if the invocation object has a transaction_hash attribute
            if hasattr(invocation, 'transaction_hash'):
                await account.client.wait_for_tx(invocation.transaction_hash)
            else:
                # If there's no transaction_hash, we'll assume the transaction is already processed
                print("No transaction hash available, assuming transaction is processed")
            
            print("Mood change completed")
        except Exception as e:
            print(f"Error in change_mood: {e}")
            raise

class LocalModel:
    def __init__(self, model: str, npc_contract):
        self.model = model
        self.npc_contract = npc_contract
        self.ollama_url = "http://localhost:11434/api/generate"

    async def get_mood(self) -> str:
        """Get the current mood of the NPC."""
        return await self.npc_contract.get_mood()

    async def change_mood(self, mood: str) -> None:
        """Set the mood of the NPC."""
        await self.npc_contract.change_mood(mood)

    def get_functions(self) -> str:
        return """
        <tools>
        {"type": "function", "function": {"name": "get_mood", "description": "get_mood() -> str - Get the current mood of the NPC.", "parameters": {"type": "object", "properties": {}}}}
        {"type": "function", "function": {"name": "change_mood", "description": "change_mood(mood: str) -> None - Set the mood of the NPC.", "parameters": {"type": "object", "properties": {"mood": {"type": "string"}}, "required": ["mood"]}}}
        </tools>
        """

    def generate_full_completion(self, prompt: str) -> dict:
        params = {"model": self.model, "prompt": prompt, "stream": False}
        try:
            response = requests.post(
                self.ollama_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(params),
                timeout=60,
            )
            response.raise_for_status()
            return json.loads(response.text)
        except requests.RequestException as err:
            return {"error": f"API call error: {str(err)}"}

    async def chat_completion_with_function_calls(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            system_message = f"""<|im_start|>system
You are a function calling AI model. You are provided with function signatures within <tools></tools> XML tags. You may call one or more functions to assist with the user query. Don't make assumptions about what values to plug into functions. Here are the available tools: {self.get_functions()} Use the following pydantic model json schema for each tool call you will make: {{"properties": {{"arguments": {{"title": "Arguments", "type": "object"}}, "name": {{"title": "Name", "type": "string"}}}}, "required": ["arguments", "name"], "title": "FunctionCall", "type": "object"}} For each function call return a json object with function name and arguments within <tool_call></tool_call> XML tags as follows:
<tool_call>
{{"arguments": <args-dict>, "name": <function-name>}}
</tool_call><|im_end|>"""

            prompt = system_message
            for message in messages:
                prompt += f"\n<|im_start|>{message['role']}\n{message['content']}<|im_end|>"
            prompt += "\n<|im_start|>assistant\n"

            response = self.generate_full_completion(prompt)
            content = response.get('response', '')

            function_call = self.parse_function_call(content)
            if function_call:
                function_name, arguments = function_call
                result = await self.process_function_call(function_name, arguments)
                return {"content": result, "function_call": {"name": function_name, "arguments": arguments}}
            
            return {"content": content.strip()}
        except Exception as e:
            print(f"Chat Completion Error: {e}")
            return {"content": f"I apologize, but I encountered an error while processing your request: {e}"}

    def parse_function_call(self, content: str) -> tuple:
        function_match = re.search(r'{\s*"arguments":\s*({.*?}),\s*"name":\s*"(\w+)"\s*}', content, re.DOTALL)
        if function_match:
            try:
                arguments = json.loads(function_match.group(1))
                function_name = function_match.group(2)
                return (function_name, arguments)
            except json.JSONDecodeError:
                print(f"Failed to parse function-like JSON: {function_match.group(0)}")
        return None

    async def process_function_call(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """Process the function call made by the LLM."""
        print(f"Processing function call: {function_name}")
        try:
            if function_name == "get_mood":
                mood = await self.get_mood()
                print(f"Current mood: {mood}")
                return f"The current mood is: {mood}"
            elif function_name == "change_mood":
                mood = arguments.get("mood", "")
                await self.change_mood(mood)
                print(f"Mood set to: {mood}")
                return f"Mood has been set to: {mood}"
        except Exception as e:
            print(f"Error during function call: {e}")
            return f"An error occurred while processing the function call: {e}"