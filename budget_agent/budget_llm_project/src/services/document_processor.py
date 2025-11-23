class DocumentProcessor:
    @staticmethod
    def create_documents_with_headers(documents, header_row=1):
        headers = [str(cell["value"]) for cell in documents[header_row - 1]]
        doc_list = []
        for row_cells in documents[header_row:]:
            text_parts = []
            for h, cell in zip(headers, row_cells):
                text_parts.append(f"{h}: {cell['value']}")
            text = " | ".join(text_parts)
            metadata = {"sheet": row_cells[0]["sheet"], "row": row_cells[0]["row"]}
            doc_list.append({"text": text, "metadata": metadata})
        return doc_list

    @staticmethod
    def chunk_documents(doc_list, chunk_size=32):
        for i in range(0, len(doc_list), chunk_size):
            yield doc_list[i:i + chunk_size]
