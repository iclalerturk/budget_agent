import re
from budget_llm_project.src.utils.utils import execute_instruction
from budget_llm_project.src.history.history_manager import HistoryManager


class QueryEngine:
    def __init__(self, llm_client):
        self.llm = llm_client
        self.history = HistoryManager()

    def _format_history(self, last: int = 5) -> str:
        items = self.history.get_last(last)
        if not items:
            return ""
        lines = []
        for it in items:
            q = it.get("question", "")
            a = it.get("answer", "")
            lines.append(f"- Soru: {q}\n  Cevap: {a}")
        return "\n".join(lines)

    @staticmethod
    def clean_json_string(json_str: str) -> str:
        """GPT'den gelen JSON string'ini temizle ve parse edilebilir hale getir."""
        if json_str.startswith("```"):
            json_str = "\n".join(json_str.split("\n")[1:-1])
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'\bnull\b', '{}', json_str)
        return json_str.strip()

    def analyze_question(self, question: str, columns: list[str]) -> str:
        """Kullanıcının sorusunu JSON formatına çevirir."""
        history_text = self._format_history(5)
        prompt = f"""
        Sen bir tablo analiz uzmanısın.
        Önceki soru-cevap geçmişi (referans olabilir, hatalıysa görmezden gel):
        {history_text}
        Kullanıcının sorusunu JSON formatında çevir.
        Kolonlar: {columns}
        İşlem tipleri: sum|max|min|avg|list|diff|percentage_change|ratio
        Gruplama desteği: group_by ile bir veya birden fazla kolona göre grupla.
        Kullanıcı ‘X dönemi itibariyle’ veya ‘X ayı itibariyle’ diye sorarsa, x ayı dahil önceki tüm ayların sonucunu hesapla ve topla.

        Eğer kullanıcı sorusunda spesifik bir ayı sormuyor tüm ayların toplamını istiyorsa ilgili sutunları bir liste halinde "target" içine yaz.
        Soruda gider diyorsa ilgili ayların fiilisi, bütçe diyorsa ilgili ayların bütçe sutunlarını topla.
        Sapma işlemi ilgili ayın fiili ile bütçesi arasındaki farktır.
        - Eğer mode = 'seperate' ise, her ayın sapmasını ayrı ayrı hesapla.
        - Eğer extra_operations içinde 'max' varsa, her ayın sapması üzerinden en büyük değeri al; toplam sapmayı asla hesaplama.
        - mode = 'together' ise, ilgili ayların fiili ile bütçesi arasındaki farkı topla ve ekstra işlemleri uygula.
        - Soru "hangi X'te en çok ..." gibi grup bazlı maksimumu soruyorsa: ilgili X kolonunu "group_by" olarak ayarla, mode = "together" seç. Her grup için toplam sonucu hesapla ve gruplar arasında en büyük değeri seç (extra_operations içine "max" ekleyebilirsin).
        Tek kolon gerekiyorsa string döndür, birden fazla kolon varsa liste döndür.
        Eğer diff işlemi ise, iki kolon arasındaki farkı belirtebiliyorsan "source" kolonunu da belirt.
        Eğer kullanıcı sorusunda bir değer (ör: "kaleseramik arge merkezi") geçiyorsa ve bu bir kolonun (ör: 'Masraf yeri') değerine karşılık geliyorsa, bunu "filter" kısmına ekle.
        Yapılacak işlemi ve extra işlemleri düzgün bir şekilde belirtmen gerekiyor, örneğin ayların sapmalarının en büyüğünü istiyorsa burada "operation": "diff", "extra_operations": ["max"] gibidir. yapılcak işlemlerin sırasını bul ona göre operation ve extra_operations kısımlarını doldur.
        - Eğer poperation "diff" veya "percentage_change" işlemi ise ve hesaplanacak sadece 2 kolon varsa:
        - "target": ilk kolon (karşılaştırılacak olan)
        - "source": ikinci kolon (referans alınacak olan)
        
        "yüzde kaç arttı / azaldı" → percentage_change
        "yüzde kaçını oluşturuyor / oranı nedir" → ratio
        Target ve source filter kısmında filtrenin ikisine ya da tekine uygulanması gerektiğine karar ver, ona göre filter kısmını doldur.
        
        JSON formatı:
        {{
            "operation": "...",
            "target": "..." veya ["...", "..."],
            "source": "..." veya ["...", "..."],  # opsiyonel, diff için ikinci kolon
            "target_filter": {{ "KolonAdı": "Değer" }} veya null
            "source_filter": {{ "KolonAdı": "Değer" }} veya null
            "mode": "seperate" | "together"
            "group_by": "KolonAdı" veya ["KolonAdı1", "KolonAdı2"],  # opsiyonel, grup bazlı hesaplar için
            "extra_operations": ["sum", "diff", "percentage_change"]  # opsiyonel
        }}

    Açıklama:
    - "mode":
        - "seperate" → Her kolonu ayrı ayrı hesapla (ay ay sonuç).
        - "together" → Kolonları toplayıp tek sonuç üret (toplam değer).
    - "extra_operations": Eğer kullanıcı ek işlemler istiyorsa (ör: sum, diff, percentage_change gibi) bunları liste halinde ekle. Kullanıcı direkt olarak ek işlemi belirtmemiş olabilir; sorudan anlaman gerekiyor.    Dikkat:
    - Kullanıcı "toplam", "hepsi beraber", "genel toplam" gibi ifaderlerle sonuç isterse → mode = "together".
    - Kullanıcı "ay ay", "her biri", "tek tek" gibi ifadelerle sonuç isterse → mode = "seperate".
        - Grup bazlı sorularda (ör: "En çok sapma hangi masraf yerinde?") → "group_by" ilgili kolonu belirt, mode = "together" seç, operation = "diff" seç, target = fiili kolon(lar), source = bütçe kolon(lar), gerekirse extra_operations = ["max"].
    - Eğer belirtilmemişse varsayılan "seperate" seç.
        DO NOT give explanations. DO NOT ask me anything. ONLY RETURN JSON.
        Soru: {question}
        """
        response = self.llm.ask(prompt)
        return self.clean_json_string(response)

    def execute_instruction(self, doc_list: list, instruction_json: str):
        """execute_instruction util fonksiyonunu çağırır."""
        return execute_instruction(doc_list, instruction_json)

    def finalize_answer(self, question: str, result):
        """Multi-target sonucu doğal dilde stringe çevirir ve LLM ile son halini hazırlar."""
        # Eğer result bir dict ise, her kolon için ayrı cevap oluştur
        if isinstance(result, dict):
            answer_parts = [f"{k}: {v}" for k, v in result.items()]
            result_str = "; ".join(answer_parts)
        else:
            result_str = str(result)

        history_text = self._format_history(3)
        prompt = f"""
        Kullanıcının sorusu: {question}
        Önceki soru-cevap geçmişi (tutarlılık için referans olabilir):
        {history_text}
        Hesaplanan sonuç: {result_str}

        Lütfen kullanıcıya doğal dilde açık bir cevap yaz. Soru sorma, sadece cevap ver. Seçenek sunma, sadece hesapladığını anlat.
        """
        return self.llm.ask(prompt)

    def smart_query(self, question: str, doc_list: list, index=None):
        """Kullanıcı sorusunu analiz eder, instruction uygular ve doğal dil cevabını döndürür."""
        # Kolon isimlerini doc_list üzerinden al
        columns = [part.split(":")[0] for part in doc_list[0]["text"].split(" | ")]
        # Kullanıcının sorusunu JSON'a çevir
        instr_json = self.analyze_question(question, columns)
        # JSON instruction'a göre tabloyu işle
        result = self.execute_instruction(doc_list, instr_json)
        # Sonucu LLM ile doğal dil cevap haline getir
        final_answer = self.finalize_answer(question, result)
        # History'e yaz
        try:
            self.history.append(
                question=question,
                instruction_json=instr_json,
                result=result,
                final_answer=final_answer,
            )
        except Exception as e:
            print("History append failed:", e)
        return final_answer

    def get_history(self, last: int = 20):
        return self.history.get_last(last)
