import streamlit as st
from PIL import Image, ImageOps
import numpy as np
import io
import pandas as pd
import zipfile

st.title("👩‍🏫 学生用固定シェアB生成アプリ")

st.write("""
授業で使う固定シェアBを、学生ごとに自動生成して配布します。
各学生はこの shareB を持っておくことで、授業ごとの shareA と合成してQRを復号できます。
""")

# 1. 元となるQRコード画像（白黒）
uploaded_qr = st.file_uploader("元QRコード画像をアップロードしてください", type=["png","jpg","jpeg"])
# 2. 学生リスト
uploaded_csv = st.file_uploader("学生リストCSVをアップロードしてください（1列: student_id）", type=["csv"])

if uploaded_qr and uploaded_csv:
    # QR画像を白黒化
    base = Image.open(uploaded_qr).convert("1")
    np_base = np.array(base, dtype=np.uint8)

    # 学生リスト読み込み
    df_students = pd.read_csv(uploaded_csv)
    student_ids = df_students.iloc[:,0].tolist()

    # ZIPでまとめる
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for sid in student_ids:
            # 学生ごとのランダム shareB
            shareB = np.random.randint(0, 2, np_base.shape, dtype=np.uint8)
            imgB = Image.fromarray((1 - shareB) * 255)

            # 保存用バッファ
            buf = io.BytesIO()
            imgB.save(buf, format="PNG")
            buf.seek(0)

            # ZIPに追加
            zf.writestr(f"{sid}_shareB.png", buf.read())

    st.download_button("📥 学生用シェアBをZIPでダウンロード", zip_buffer.getvalue(), "shareB_students.zip")
    st.success(f"{len(student_ids)}人分の固定シェアBを生成しました。")
