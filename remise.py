import pdfplumber
import re
import pandas as pd

def extraire_remise(pdf_path):
    lignes = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()

            # Trouver la date de remise
            match_date = re.search(r"\d{2}/\d{2}/\d{2}", text)
            date_remise = match_date.group(0) if match_date else ""

            # Trouver chaque ligne de chèque
            matches = re.findall(r"/\s*([A-ZÉÈA-Z\s]+)\s+([\d\s,]+)", text)
            for tireur, montant in matches:
                tireur_clean = tireur.strip().split()[0]
                compte = f"4110{tireur_clean[0].upper()}"
                montant_float = float(montant.replace(" ", "").replace(",", "."))
                lignes.append([date_remise, "OD", compte, "", montant_float])

            # Total de la remise
            match_total = re.search(r"Total de la remise\s*:\s*([\d\s,]+)", text)
            if match_total:
                total = float(match_total.group(1).replace(" ", "").replace(",", "."))
                lignes.append([date_remise, "OD", "5112", total, ""])

    df = pd.DataFrame(lignes, columns=["Date", "Journal", "Compte", "Débit", "Crédit"])
    df.to_excel("remise_cheques_ecritures.xlsx", index=False)
    print("✅ Fichier généré : remise_cheques_ecritures.xlsx")

extraire_remise("30) 23-09-25 Remise de cheque.pdf")