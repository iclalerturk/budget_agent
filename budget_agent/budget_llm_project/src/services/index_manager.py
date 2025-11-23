class IndexManager:
    def __init__(self):
        self.index = None
        self.embeddings = None

    def build_index_for_sheet(self, doc_list, sheet_name):
        subset = [doc for doc in doc_list if doc["metadata"]["sheet"] == sheet_name]
        embeddings = None
        index = None
        self.index = index
        self.embeddings = embeddings
        return index, subset, embeddings
