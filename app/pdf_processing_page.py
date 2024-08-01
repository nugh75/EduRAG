# pdf_processing_page.py

import os
import logging
from concurrent.futures import ThreadPoolExecutor
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

def pdf_processing_page():
    # Configurazione del logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Titolo dell'applicazione Streamlit
    st.title("PDF Processor with FAISS Indexing")

    # Input dell'utente tramite Streamlit
    folder_path = st.text_input("Percorso della cartella contenente i PDF:", "/home/nugh75/git-repository/Edubot/emedia-M")
    chunk_size = st.number_input("Dimensione dei chunk di testo:", min_value=100, max_value=5000, value=1500)
    chunk_overlap = st.number_input("Sovrapposizione tra i chunk:", min_value=0, max_value=1000, value=200)
    min_chunk_length = st.number_input("Lunghezza minima di un chunk:", min_value=50, max_value=1000, value=100)
    embeddings_model_name = st.text_input("Nome del modello di embeddings:", "sentence-transformers/all-MiniLM-L12-v2")
    faiss_index_folder = st.text_input("Nome della cartella per l'indice FAISS:", "OFA")

    # Bottone per iniziare il processamento
    if st.button("Esegui"):
        # Funzione per caricare documenti PDF
        def load_pdf(file_path):
            try:
                loader = PyPDFLoader(file_path=file_path)
                documents = loader.load()
                logging.info(f"Caricato: {file_path}")
                return documents
            except Exception as e:
                logging.error(f"Errore nel caricamento del file {file_path}: {e}")
                return []

        # Lista per memorizzare tutti i documenti caricati
        all_documents = []

        # Verifica se la cartella esiste
        if os.path.exists(folder_path):
            # Caricamento parallelo dei documenti PDF
            with ThreadPoolExecutor() as executor:
                futures = []
                for filename in os.listdir(folder_path):
                    if filename.endswith(".pdf"):
                        pdf_path = os.path.join(folder_path, filename)
                        futures.append(executor.submit(load_pdf, pdf_path))
                
                for future in futures:
                    all_documents.extend(future.result())

            # Funzione per formattare i documenti
            def format_documents(documents):
                return "\n\n".join(doc.page_content for doc in documents if hasattr(doc, 'page_content'))

            # Inizializzare il Text Splitter
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )

            # Suddividere i documenti in chunk
            splits = text_splitter.split_documents(all_documents)

            # Rimuovere i chunk troppo piccoli
            splits = [sp for sp in splits if len(sp.page_content) >= min_chunk_length]

            # Inizializzare il modello di embedding
            embeddings = HuggingFaceEmbeddings(model_name=embeddings_model_name)

            # Creare o caricare l'indice FAISS
            try:
                if os.path.exists(faiss_index_folder) and os.path.exists(os.path.join(faiss_index_folder, "index.faiss")):
                    # Caricare indice FAISS dalla cartella
                    faiss_index = FAISS.load_local(
                        faiss_index_folder,
                        embeddings,
                        allow_dangerous_deserialization=True
                    )
                    logging.info("Indice FAISS caricato correttamente.")
                    st.success("Indice FAISS caricato correttamente.")
                else:
                    # Creare indice FAISS dai chunk
                    faiss_index = FAISS.from_documents(
                        splits,
                        embeddings
                    )
                    # Creare la cartella se non esiste
                    os.makedirs(faiss_index_folder, exist_ok=True)
                    faiss_index.save_local(faiss_index_folder)
                    logging.info("Indice FAISS creato e salvato correttamente.")
                    st.success("Indice FAISS creato e salvato correttamente.")
            except Exception as e:
                logging.error(f"Errore durante la gestione dell'indice FAISS: {e}")
                st.error(f"Errore durante la gestione dell'indice FAISS: {e}")
        else:
            st.error("La cartella specificata non esiste.")
