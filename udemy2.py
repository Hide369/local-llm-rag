from datetime import datetime  # <--- 追加
import streamlit as st
from openai import OpenAI

# 今日の日付を取得 (例: 2026年08月09日)
today_str = datetime.today().strftime("%Y年%m月%d日")

st.set_page_config(page_title="Local LLM Chat")  
st.sidebar.title("設定") 
 
# モデル名の入力欄をサイドバーに追加
model = st.sidebar.text_input("モデル名", value="llama3.1:8b") 

# Temperatureのスライダーをサイドバーに追加
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.3, step=0.1) 

# プロンプトの入力欄をサイドバーに追加（初期値に今日の日付を含める）
system_prompt = st.sidebar.text_area(
    "System Prompt", 
    f"あなたは有能なアシスタントです。今日の日付は{today_str}です。日本語で回答して下さい。"
)  

# タイトル
st.title("Local LLM Chat")

# 会話の履歴を保管
if "messages" not in st.session_state:
    st.session_state.messages = []

# 会話の履歴をリセット
if st.sidebar.button("会話履歴をリセット"):
    st.session_state.messages = []
    st.success("会話履歴をリセットしました。")

# 会話履歴を表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

client = OpenAI(
    api_key="ollama",  # OllamaのAPIキー（ダミー値で可）
    base_url="http://localhost:12000/v1"  # ローカルOllamaサーバの指定
)

# プロンプトの入力欄（入力されるまでは None になる）
prompt = st.chat_input("メッセージを入力")  

# ユーザーがメッセージを入力して送信したときだけ実行する
# ユーザーがメッセージを入力して送信したときだけ実行する
if prompt:
    # ユーザーの入力を画面と履歴に追加
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # APIに渡すmessages配列を作成（会話履歴を含める）
    if system_prompt.strip():  # system_promptが空でない場合のみ追加
        messages_for_api = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    else:
        messages_for_api = st.session_state.messages

    # アシスタントの回答エリアを作成してストリーミング表示
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=model,
            messages=messages_for_api,
            temperature=temperature,
            stream=True  # ストリーミングモードを有効化
        )
        # st.write_stream にジェネレータ関数を渡して出力と結果取得を同時に行う
        def response_generator():
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        bot_response = st.write_stream(response_generator())

    # 会話履歴にアシスタントの回答を追加
    st.session_state.messages.append({"role": "assistant", "content": bot_response})