from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# Load NER model
tokenizer = AutoTokenizer.from_pretrained("d4data/biomedical-ner-all")
model = AutoModelForTokenClassification.from_pretrained("d4data/biomedical-ner-all")

ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")


def extract_entities(text: str):
    """
    Extract medical entities using Hugging Face NER.
    Returns a list of extracted entities.
    """
    entities = ner_pipeline(text)
    return [ent['word'] for ent in entities if len(ent['word']) > 2]  # filter tiny tokens
