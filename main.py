import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import numpy as np
import io

st.set_page_config(page_title="GCash OCR - EasyOCR", layout="wide")
st.title("📝 GCash Form Scanner - EasyOCR FREE")

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr()

def extract_table(image):
    """Extract table using EasyOCR"""
    img_array = np.array(image)
    
    # Run OCR
    results = reader.readtext(img_array)
    
    # Parse results
    all_text = []
    for (bbox, text, confidence) in results:
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_center = (bbox[0][0] + bbox[2][0]) / 2
        all_text.append({
            'text': text,
            'x': x_center,
            'y': y_center,
            'conf': confidence
        })
    
    # Group by rows based on Y position
    all_text.sort(key=lambda x: x['y'])
    rows = []
    current_row = []
    last_y = -50
    
    for item in all_text:
        if abs(item['y'] - last_y) > 20: # New row threshold
            if current_row:
                rows.append(current_row)
            current_row = [item]
            last_y = item['y']
        else:
            current_row.append(item)
    
    if current_row:
        rows.append(current_row)
    
    # Sort each row by X and build table
    table_data = []
    for row in rows:
        row.sort(key=lambda x: x['x'])
        row_texts = [item['text'] for item in row if item['conf'] > 0.3]
        
        # Try to fit into 5 columns: NAME, STORE, PHONE, GCASH, SIGNATURE
        if len(row_texts) >= 1 and any(c.isalpha() for c in row_texts[0]):
            while len(row_texts) < 5:
                row_texts.append('')
            table_data.append(row_texts[:5])
    
    return table_data

uploaded_file = st.file_uploader("Upload GCash Form Photo", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ready to scan", use_column_width=True)
    
    if st.button("🔍 Run AI Scan", type="primary"):
        with st.spinner('EasyOCR is reading... ~10-20 seconds'):
            try:
                table_data = extract_table(image)
                
                if table_data:
                    st.success(f"✅ Extracted {len(table_data)} rows!")
                    
                    df = pd.DataFrame(table_data, columns=[
                        'NAME',
                        'STORE NAME', 
                        'PHONE NUMBER',
                        'GCASH VERIFIED ACCOUNT?',
                        'SIGNATURE'
                    ])
                    
                    st.subheader("📋 Verify Data - Edit mo kung may mali")
                    edited_df = st.data_editor(
                        df,
                        num_rows="dynamic",
                        use_container_width=True,
                        height=400
                    )
                    
                    csv = edited_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        "gcash_form.csv",
                        "text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("No table detected. Crop mo muna yung image para table lang yung kita.")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")
else:
    st.info("👆 Upload a GCash form photo to start")
    st.success("✅ 100% FREE - EasyOCR, No internet needed after install")