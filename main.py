import asyncio
from npc_model import NPCContract, LocalModel

OLLAMA_MODEL = "taozhiyuai/hermes-2-theta-llama-3:8b-f16"

PRIVATE_KEY = "0x2bbf4f9fd0bbb2e60b0316c1fe0b76cf7a4d0198bd493ced9b8df2a3a24d68a"
ACCOUNT_ADDRESS = "0xb3ff441a68610b30fd5e2abbf3a1548eb6ba6f3559f2862bf2dc757e5828ca"
CONTRACT_ADDRESS = "0x015528953d169170925f84b3589f34de521d4adaff504dcda5a31f05c499ba16"

async def main():
    try:
        print("Initializing NPCContract...")
        npc_contract = NPCContract(
            node_url="http://0.0.0.0:5050",
            private_key=PRIVATE_KEY,
            account_address=ACCOUNT_ADDRESS,
            contract_address=CONTRACT_ADDRESS
        )

        print("Initializing LocalModel...")
        llm = LocalModel(model=OLLAMA_MODEL, npc_contract=npc_contract)

        messages = [
            {"role": "system", "content": "You are an NPC named Alastair in the world of Lord of the Rings. You can check and update your mood based on the conversation. Use the get_mood function to check your current mood, and the change_mood function to update it when appropriate based on the conversation context."}
        ]

        print("You are talking to Alastair. Type 'exit' to end the conversation.")

        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                break

            messages.append({"role": "user", "content": user_input})

            response = await llm.chat_completion_with_function_calls(messages)
            print(f"Received response: {response}")

            if "function_call" in response:
                function_name = response["function_call"]["name"]
                arguments = response["function_call"]["arguments"]
                result = response["content"]
                print(f"Function {function_name} called with arguments {arguments}. Result: {result}")
                messages.append({"role": "function", "name": function_name, "content": result})
                
                # Get a new response based on the function call result
                response = await llm.chat_completion_with_function_calls(messages)
                content = response["content"]
            else:
                content = response["content"]

            messages.append({"role": "assistant", "content": content})
            print(f"Alastair: {content}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())