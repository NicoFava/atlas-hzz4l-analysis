#!/usr/bin/env python3
import os
import sys

try:
    import ROOT
except Exception as e:
    print('ERRORE: PyROOT è necessario per eseguire questo script.')
    sys.exit(1)

# Impostazioni grafiche stile ATLAS per un plot pulito
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)  # Nasconde il box statistico (Entries, Mean, ecc.)
ROOT.gStyle.SetPadTickX(1)
ROOT.gStyle.SetPadTickY(1)
ROOT.gStyle.SetTitleFont(42, "XYZ")
ROOT.gStyle.SetTitleSize(0.05, "XYZ")
ROOT.gStyle.SetLabelFont(42, "XYZ")
ROOT.gStyle.SetLabelSize(0.04, "XYZ")
ROOT.gStyle.SetLegendBorderSize(0)
ROOT.gStyle.SetLegendFont(42)
ROOT.gStyle.SetFrameLineWidth(1)

# ==========================================
# CONFIGURAZIONE DATASET
# ==========================================
# Directory principale del progetto e cartella output
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_ROOT = os.path.join(PROJECT_ROOT, "output")

# Liste basate sulla slide della tua professoressa
FONDI = [
    {"id": "mc_363490", "nome": "ZZ 4l", "colore": ROOT.kRed - 4},
    {"id": "mc_363356", "nome": "ZZ qq2l", "colore": ROOT.kYellow},
    {"id": "mc_363491", "nome": "WZ 3l", "colore": ROOT.kViolet}
]

SEGNALI = [
    "mc_345060", # ggF ZZ 4l
    "mc_344235", # VBF ZZ 4l
    "mc_341947", # ZH ZZ 4l
    "mc_341964", # WH ZZ 4l
    "mc_345337", # ZH WW 4l
    "mc_341122", # ggF ZZ tautaull
    "mc_341155"  # VBF ZZ tautaull
]

DATI = ["data_A", "data_B", "data_C", "data_D"]

# Variabile da plottare
HISTO_NAME = "m_Higgs"
# ==========================================

def get_output_dir(identifier):
    """Ritorna la cartella di output associata a un dataset MC o dati."""
    if identifier.startswith("analysis_output_") or identifier.startswith("output_data_"):
        return os.path.join(OUTPUT_ROOT, identifier)

    if identifier.startswith("mc_"):
        run_id = identifier.split("mc_", 1)[1]
        return os.path.join(OUTPUT_ROOT, f"analysis_output_{run_id}")

    if identifier.startswith("data_"):
        suffix = identifier.split("data_", 1)[1]
        return os.path.join(OUTPUT_ROOT, f"output_data_{suffix}")

    return os.path.join(OUTPUT_ROOT, identifier)


def get_histogram(dir_name, hist_name):
    """Apre il file ROOT nella cartella specificata e recupera l'istogramma."""
    output_dir = get_output_dir(dir_name)
    file_path = os.path.join(output_dir, "analysis_histograms.root")
    
    if not os.path.exists(file_path):
        print(f"ATTENZIONE: File non trovato -> {file_path}")
        return None
        
    f = ROOT.TFile.Open(file_path, "READ")
    h = f.Get(hist_name)
    if not h:
        print(f"ATTENZIONE: Istogramma {hist_name} non trovato in {file_path}")
        f.Close()
        return None
        
    h.SetDirectory(0) # Sgancia l'istogramma dal file per tenerlo in memoria
    f.Close()
    return h

def main():
    print("Inizio la costruzione del Money Plot...")

    # 1. Prepariamo la Canvas e la Legenda
    canvas = ROOT.TCanvas("canvas", "Higgs Discovery", 900, 700)
    canvas.SetMargin(0.12, 0.05, 0.12, 0.05) # Sinistra, Destra, Basso, Alto

    legend = ROOT.TLegend(0.55, 0.72, 0.88, 0.90)    
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.SetTextSize(0.032)
    legend.SetTextFont(42)

    # 2. Creiamo la Pila (THStack) per i fondi e il segnale
    stack = ROOT.THStack("hs", ";m_{4l} [GeV];Events")

    # 3. Aggiungiamo i Fondi alla pila (uno per uno per colorarli diversamente)
    for fondo in FONDI:
        h_fondo = get_histogram(fondo["id"], HISTO_NAME)
        if h_fondo:
            h_fondo.SetFillColor(fondo["colore"])
            h_fondo.SetFillStyle(1001)
            h_fondo.SetLineColor(ROOT.kBlack)
            h_fondo.SetLineWidth(1)
            stack.Add(h_fondo)
            legend.AddEntry(h_fondo, f"{fondo['nome']}", "f")

    # 4. Aggiungiamo i Segnali (li sommiamo tutti in un unico istogramma rosso)
    h_segnale_tot = None
    for sig in SEGNALI:
        h_sig = get_histogram(sig, HISTO_NAME)
        if h_sig:
            if h_segnale_tot is None:
                h_segnale_tot = h_sig.Clone("h_segnale_tot")
            else:
                h_segnale_tot.Add(h_sig)
                
    if h_segnale_tot:
        h_segnale_tot.SetFillColor(ROOT.kAzure + 7)
        h_segnale_tot.SetLineColor(ROOT.kBlack)
        h_segnale_tot.SetLineWidth(1)
        stack.Add(h_segnale_tot) # Lo mettiamo in cima alla pila!
        legend.AddEntry(h_segnale_tot, "Higgs (125 GeV)", "f")

    # 5. Aggiungiamo i Dati veri (li sommiamo tutti)
    h_dati_tot = None
    for data_dir in DATI:
        h_d = get_histogram(data_dir, HISTO_NAME)
        if h_d:
            if h_dati_tot is None:
                h_dati_tot = h_d.Clone("h_dati_tot")
            else:
                h_dati_tot.Add(h_d)
                
    if h_dati_tot:
        h_dati_tot.SetMarkerStyle(20) # Pallini pieni neri
        h_dati_tot.SetMarkerSize(1.1)
        h_dati_tot.SetLineColor(ROOT.kBlack)
        legend.AddEntry(h_dati_tot, "Data 13 TeV", "pe")

    # 6. Disegniamo tutto
    # Disegniamo prima la pila (Fondi + Segnale)
    stack.Draw("HIST")
    
    # Sistimiamo gli assi della pila per farci stare i dati
    massimo_stack = stack.GetMaximum()
    massimo_dati = h_dati_tot.GetMaximum() if h_dati_tot else 0
    stack.SetMaximum(max(massimo_stack, massimo_dati) * 1.3) # +30% di spazio sopra
    
    stack.GetXaxis().SetTitleSize(0.045)
    stack.GetYaxis().SetTitleSize(0.045)
    stack.GetXaxis().SetLabelSize(0.04)
    stack.GetYaxis().SetLabelSize(0.04)
    stack.GetXaxis().SetRangeUser(0, 160)
    stack.SetMinimum(0.1)

    if h_dati_tot:
        bin_width = (160.0 - 110.0) / h_dati_tot.GetNbinsX()
        stack.SetTitle(f";m_{{4l}} [GeV];Events / {bin_width:.2f} GeV")

    # Disegniamo i Dati sovrapposti con le barre d'errore (PE1)
    if h_dati_tot:
        h_dati_tot.Draw("PE1 SAME")

    legend.Draw("SAME")
    
    # Aggiungiamo le scritte classiche di ATLAS
    testo = ROOT.TLatex()
    testo.SetNDC()
    testo.SetTextFont(72)
    testo.SetTextSize(0.05)
    testo.DrawLatex(0.15, 0.85, "ATLAS")
    testo.SetTextFont(42)
    testo.DrawLatex(0.28, 0.85, "Open Data")
    testo.SetTextSize(0.04)
    testo.DrawLatex(0.15, 0.80, "#sqrt{s} = 13 TeV, 10 fb^{-1}")
    testo.DrawLatex(0.15, 0.75, "H #rightarrow ZZ* #rightarrow 4l")

    # Salviamo il risultato
    out_name = "Higgs_Discovery_Plot0.png"
    canvas.SaveAs(out_name)
    canvas.SaveAs("Higgs_Discovery_Plot0.pdf")
    print(f"\nGrafico completato e salvato come {out_name}!")

if __name__ == "__main__":
    main()