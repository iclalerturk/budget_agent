# budget_llm_project

## 📌 Açıklama
Bu proje, LLM tabanlı bütçe analizi ve raporlama sistemidir.

## 📂 Proje Yapısı
```
budget_llm_project/
main.py
main2.py
readme.py
requirements.txt
data/
    veriler.xlsx
src/
    api/
        api.py
    document_processing/
        document_processor.py
        excel_reader.py
        index_manager.py
    history/
        history.jsonl
        history_manager.py
    llm/
        llm_client.py
    utils/
        query_engine.py
        utils.py
```

## 📦 Gereksinimler
- fastapi==0.116.2
- httpx==0.28.1
- openai==1.108.0
- openpyxl==3.1.5
- pandas==2.3.2
- pydantic==1.10.22
- rapidfuzz==3.14.1

## 🚀 Çalıştırma
```bash
pip install -r requirements.txt
python main.py
```
![Screenshot_20260124_215554_Canva](https://github.com/user-attachments/assets/775fa5f4-6997-4611-94c3-c4db31fc703c)
