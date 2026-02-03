import os
import shutil
import chromadb
from chromadb.utils import embedding_functions
CHROMA_PATH = "./chroma_db"

# --- THE FACTORY KNOWLEDGE BASE (50+ Data Points) ---
FACTORY_KNOWLEDGE = [
    # === SAFETY PROTOCOLS ===
    "Safety: All personnel must wear aluminized aprons and face shields within 5 meters of the Induction Furnace.",
    "Safety: In case of molten metal spill, trigger the 'Emergency Floor Dry' alarm immediately. Do NOT use water.",
    "Safety: Forklift speed limit on the shop floor is 5 km/h.",
    "Safety: Lock-out/Tag-out (LOTO) procedure must be followed before opening any electrical panel.",
    "Safety: Respirators are mandatory in the Sand Reclamation area due to silica dust.",
    "Safety: Crane inspection must be performed at the start of every shift.",
    "Safety: No loose clothing or jewelry is allowed near rotating machinery.",
    "Safety: Eye protection (ANSI Z87.1) is mandatory in the grinding area.",
    "Safety: Hearing protection is required in areas exceeding 85 dB (Fettling Shop).",
    "Safety: Heat stress breaks are mandatory every 2 hours during summer months.",

    # === MELTING OPERATIONS ===
    "Melting: Grey Iron tap temperature target is 1420°C to 1450°C.",
    "Melting: SG Iron tap temperature target is 1480°C to 1520°C.",
    "Melting: Add Ferro-Silicon inoculant only when the ladle is 1/3rd full to ensure mixing.",
    "Melting: Slag removal must be performed twice: once after melting and once before tapping.",
    "Melting: Carbon Equivalent (CE) value must be maintained between 3.9% and 4.1% for Grade 25 iron.",
    "Melting: Furnace lining life is approximately 300 heats. Check thickness daily.",
    "Melting: Do not charge wet or oily scrap into the furnace (Explosion Risk).",
    "Melting: Maximum power density for the induction furnace is 600 kW/ton.",
    "Melting: Chill wedge test must be taken for every heat before pouring.",
    "Melting: Spheroidization treatment time must not exceed 8 minutes.",

    # === MOLDING & SAND ===
    "Molding: Green Sand moisture content must be maintained between 3.0% and 3.6%.",
    "Molding: Permeability of sand should be > 120. Low permeability causes blowholes.",
    "Molding: Active Clay content target is 9-11%.",
    "Molding: Mold hardness should be minimum 85 on the B-scale.",
    "Molding: Cooling time for castings > 50kg is minimum 4 hours before shakeout.",
    "Molding: Sand temperature entering the muller should not exceed 40°C.",
    "Molding: Compactability target is 38-42% for high-pressure molding lines.",
    "Molding: Dead clay limit is 3.0%. Exceeding this requires fresh sand addition.",
    "Molding: Core setting must be verified by the supervisor for complex castings.",
    "Molding: Vent holes must be kept open to prevent gas entrapment.",

    # === QUALITY & DEFECTS ===
    "Quality: 'Blowholes' are caused by high moisture or poor venting. Fix: Reduce water ratio.",
    "Quality: 'Shrinkage' is caused by poor feeding or low carbon. Fix: Use larger risers.",
    "Quality: 'Cold Shut' is caused by low pouring temperature. Fix: Increase tap temp by 20°C.",
    "Quality: 'Sand Drop' is caused by weak sand. Fix: Increase clay bond.",
    "Quality: Grade A Castings must have zero visible porosity on machined surfaces.",
    "Quality: Spectrometer calibration must be done every morning at 6:00 AM.",
    "Quality: Brinell Hardness for Grade 25 Iron should be 180-220 BHN.",
    "Quality: Microstructure must show >90% Type A Graphite flakes.",
    "Quality: Dye Penetrant Test (DPT) is mandatory for all valve castings.",
    "Quality: First piece approval is required after any pattern change.",

    # === MAINTENANCE ===
    "Maintenance: Check hydraulic oil levels in the Molding Machine every Monday.",
    "Maintenance: Shot Blast machine blades must be replaced after 400 hours of operation.",
    "Maintenance: Grease overhead crane pulleys weekly.",
    "Maintenance: Compressor air leaks check is mandatory every Sunday shift.",
    "Maintenance: Induction Furnace cooling water conductivity must be < 5 micro-siemens.",
    "Maintenance: Vibro-feeder springs must be inspected for cracks monthly.",
    "Maintenance: Dust collector filters must be cleaned via pulse-jet every 30 minutes.",
    "Maintenance: Gearbox oil change interval is 6 months.",
    "Maintenance: Thermocouple calibration validity is 30 days.",
    "Maintenance: Emergency stop buttons must be tested weekly.",

    # === INVENTORY RULES ===
    "Inventory: Reorder Scrap Steel when stock drops below 5,000 kg.",
    "Inventory: Reorder Pig Iron when stock drops below 2,000 kg.",
    "Inventory: Ferro-Silicon must be stored in a dry area to prevent hydrogen pickup.",
    "Inventory: Resin binders have a shelf life of 3 months. Check expiry dates monthly.",
    "Inventory: Safety stock for Crucibles is 2 units.",
    "Inventory: Sleeves and filters must be kept in the dehumidified storage room.",
    "Inventory: Minimum stock for grinding wheels is 50 units.",
    "Inventory: FIFO (First-In-First-Out) must be followed for all chemical binders.",
    "Inventory: Critical spare parts list must be reviewed quarterly.",
    "Inventory: Empty gas cylinders must be stored separately from full ones."
]

def main():
    print("🚀 Initializing Native ChromaDB Memory...")

    # 1. Clear old data
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # 2. Initialize Native Client
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # 3. Setup Embedding Function (Sentence Transformers runs locally)
    # This automatically downloads 'all-MiniLM-L6-v2'
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    # 4. Create Collection
    collection = client.create_collection(name="foundry_knowledge", embedding_function=ef)

    # 5. Add Documents
    ids = [f"id_{i}" for i in range(len(FACTORY_KNOWLEDGE))]
    metadatas = [{"type": "manual"} for _ in FACTORY_KNOWLEDGE]
    
    collection.add(
        documents=FACTORY_KNOWLEDGE,
        ids=ids,
        metadatas=metadatas
    )

    print(f"✅ Successfully stored {len(FACTORY_KNOWLEDGE)} items in Native ChromaDB.")

if __name__ == "__main__":
    main()