import streamlit as st
from PIL import Image
import numpy as np
import io

# QR読み取りが必要なら有効化（opencv-python-headless が requirements に必要）
try:
    import cv2
    QR_AVAILABLE = True
except Exception:
    QR_AVAILABLE = False

st.set_page_config(page_title="出席確認（学生用）", layout="centered")
st.title("🧑‍🎓 学生用アプリ（出席確認）")

st.write("教員から配布された `shareA.png` と 自分の `shareB.png` をアップロードしてください。")

# --- アップロード ---
shareA_file = st.file_uploader("教員の shareA.png を選択", type=["png", "jpg", "jpeg"])
shareB_file = st.file_uploader("あなたの shareB.png を選択", type=["png", "jpg", "jpeg"])

def pil_to_binary_array(pil_img, size=None, threshold=128):
    """
    PIL画像を受け取り、指定サイズにリサイズしてから
    明確に二値化（0または1の配列）して返す。
    出力: numpy array dtype uint8, shape=(h,w), values 0 or 1
    Convention: 黒(pixel <= threshold) -> 1, 白 -> 0
    """
    if size is not None:
        pil_img = pil_img.resize(size, resample=Image.NEAREST)
    # グレースケール
    gray = pil_img.convert("L")
    arr = np.array(gray)
    # 閾値で二値化：黒を1にする
    bin_arr = np.where(arr <= threshold, 1, 0).astype(np.uint8)
    return bin_arr

if shareA_file and shareB_file:
    # PILで読み込む
    imgA = Image.open(shareA_file)
    imgB = Image.open(shareB_file)

    # サイズを揃える（shareBをshareAのサイズにする）
    sizeA = imgA.size  # (width, height)
    imgB = imgB.resize(sizeA, resample=Image.NEAREST)

    # 二値化（黒->1, 白->0）
    binA = pil_to_binary_array(imgA, size=sizeA, threshold=128)
    binB = pil_to_binary_array(imgB, size=sizeA, threshold=128)

    # --- ここが重要 ---
    # teacher 側の実装では：
    #   shareA, shareB は 0/1 ビットで作られており、
    #   保存時は (1 - bit) * 255 の形で PNG にした（黒が bit=1 を表す）。
    # したがって、上の binA, binB は「bit と一致」するはず。
    #
    # 復号（元の base 相当）は XOR: base = shareA ^ shareB
    reconstructed = np.bitwise_xor(binA, binB)  # 0/1
    # teacher 側で base = invert(original) をしていた場合は
    # reconstructed が invert(original) になっているはずなので
    # 元の秘密画像(original) を取り戻すには再反転する:
    original = 1 - reconstructed

    # 画像表示用に戻す
    decoded_img = Image.fromarray((original * 255).astype(np.uint8))

    st.image([imgA.convert("RGB"), imgB.convert("RGB"), decoded_img],
             caption=["アップロードされた shareA (教員)", "アップロードされた shareB (あなた)", "復号結果（予想される元画像）"],
             width=280)

    # QR読み取り（あれば）
    if QR_AVAILABLE:
        st.write("🔎 QRコード読み取りを試みます...")
        # OpenCVはBGRで読み、ここでは decoded_img を直接配列化
        decoded_arr = np.array(decoded_img.convert("L"))
        # 2値化してOpenCVに渡す（uint8）
        _, qbin = (decoded_arr <= 128).astype("uint8"), None
        # OpenCV expects single-channel image; use detectAndDecode with cv2
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode((decoded_arr).astype(np.uint8))
        if data:
            st.success(f"QRコード検出: {data}")
            st.experimental_set_query_params(q=data)  # optional: reflect in URL
            # 自動でフォーム等に飛ばしたい場合は次の行のコメントを外す
            # st.write(f"[フォームへ移動]({data})")
        else:
            st.info("QRコードは見つかりませんでした。復号画像を確認してください。")

    else:
        st.info("QR読み取りライブラリ（OpenCV）がインストールされていません。必要なら requirements に opencv-python-headless を追加してください。")

    # 出席確定の例表示
    st.success("復号処理を行いました。復号結果を確認してください。")
else:
    st.info("まずは教員の shareA.png と自分の shareB.png を両方選択してください。")
