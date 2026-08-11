from openai import OpenAI

client = OpenAI(
    api_key="ollama",  # OllamaのAPIキーを指定（仮）
    base_url="http://localhost:12000/v1"  # ローカルOllmaサーバの指定
)

response = client.chat.completions.create(
    model="llama3.1:8b",  # 使用するモデルを指定
    messages=[
        {"role": "user", "content": "こんにちは！"}
    ],
    temperature=0.3,  # 応答の多様性を制御するパラメータ（1に近い値ほど意外性がある）
    stream=True  # ストリーミングモードを有効にする
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="", flush=True)  # ストリーミングで受け取った部分を表示
