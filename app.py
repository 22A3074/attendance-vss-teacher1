# attendance_vss_student.py
import streamlit as st
from PIL import Image
import numpy as np, io, hashlib, requests, cv2

st.set_page_config(page_title="👨‍🎓 学生用復号アプリ", layout="centered")
st.title("👨‍🎓 学生用復号アプリ（QR自動読み取り + 出席送信）")

st.write("注意: 教員の配布した ShareB（自分専用）をあらかじめ保存し、授業ごとに配布される教員側の ShareA を使って復号します。復号して QR の URL を読み取った後、自分の student_id とともに教員アプリの API に送信して出席完了を記録します。")

shareA_file = st.file_uploader("教員の ShareA（授業ごと）を選択", type=["png"])
shareB_file = st.file_uploader("自分の ShareB（配布済み、固定）を選択", type=["png"])
student_id = st.text_input("Student ID（自分の学籍番号等）")
teacher_api_url = st.text_input("教員の API エンドポイント（例: https://example.com/api/record_attendance）")

if shareA_file and shareB_file:
    imgA = Image.open(shareA_file).convert("L")
    imgB = Image.open(shareB_file).convert("L").resize(imgA.size, Image.NEAREST)

    arrA = np.array(imgA)
    arrB = np.array(imgB)
    binA = 1 - (arrA // 255)
    binB = 1 - (arrB // 255)

    reconstructed = np.bitwise_xor(binA, binB)
    original = 1 - reconstructed
    decoded_img = Image.fromarray((original*255).astype(np.uint8))
    st.image(decoded_img, caption="復号結果（QR）", width=350)

    # ダウンロード可能
    buf = io.BytesIO()
    decoded_img.save(buf, format="PNG")
    st.download_button("📥 復号画像をダウンロード", buf.getvalue(), "decoded.png")

    # QR 読み取り（OpenCV）
    cv_img = np.array(decoded_img)
    qr_detector = cv2.QRCodeDetector()
    data, bbox, _ = qr_detector.detectAndDecode(cv_img)
    if data:
        st.success("QRコード読み取り成功！")
        st.write("QR の中身（URL 等）:")
        st.code(data)
        # attempt to parse class_id from URL query param class=... (if present)
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(data)
        q = parse_qs(parsed.query)
        class_id = q.get("class", [None])[0]
        st.write(f"検出された class_id: {class_id}")

        # compute shareB hash
        shareb_bytes = open(shareB_file.name, "rb").read() if hasattr(shareB_file, "name") and shareB_file.name else buf.getvalue()
        # safer: read bytes from uploaded file
        shareB_file.seek(0)
        shareb_bytes = shareB_file.read()
        sha = hashlib.sha256(shareb_bytes).hexdigest()
        st.write(f"自分の ShareB SHA256: `{sha}`")

        if st.button("✅ 出席を教員に送信する（Mark Attendance）"):
            if not student_id:
                st.error("student_id を入力してください。")
            elif not teacher_api_url:
                st.error("教員の API URL を入力してください。")
            else:
                payload = {
                    "student_id": student_id,
                    "shareb_hash": sha,
                    "class_id": class_id if class_id else "unknown",
                    "source_url": data
                }
                try:
                    resp = requests.post(teacher_api_url, json=payload, timeout=10)
                    if resp.ok:
                        st.success("出席を記録しました。教員の出席表を確認してください。")
                        st.json(resp.json())
                    else:
                        st.error(f"サーバーがエラーを返しました: {resp.status_code} {resp.text}")
                except Exception as e:
                    st.error(f"送信に失敗しました: {e}")
    else:
        st.warning("QRコードの読み取りに失敗しました。復号画像が小さい/ぼやけている可能性があります。")
