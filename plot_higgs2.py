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
ROOT.gStyle.SetOptStat(0)  # Nasconde il box statistico
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
    print("Inizio la costruzione del Money Plot Ufficiale...")

    # 1. Prepariamo la Canvas divisa in due (Pad principale + Ratio Pad)
    canvas = ROOT.TCanvas("canvas", "Higgs Discovery", 900, 850)
    
    # Pad Superiore (70% dello spazio)
    pad1 = ROOT.TPad("pad1", "pad1", 0, 0.3, 1, 1.0)
    pad1.SetBottomMargin(0.03) # Margine piccolissimo per incollarsi al pad inferiore
    pad1.SetLeftMargin(0.12)
    pad1.SetRightMargin(0.05)
    pad1.SetTopMargin(0.08)
    pad1.Draw()
    
    # Pad Inferiore (30% dello spazio)
    canvas.cd()
    pad2 = ROOT.TPad("pad2", "pad2", 0, 0, 1, 0.3)
    pad2.SetTopMargin(0.0)
    pad2.SetBottomMargin(0.35)
    pad2.SetLeftMargin(0.12)
    pad2.SetRightMargin(0.05)
    pad2.Draw()

    # ==========================================
    # PAD 1: GRAFICO PRINCIPALE
    # ==========================================
    pad1.cd()

    legend = ROOT.TLegend(0.55, 0.65, 0.88, 0.88)    
    legend.SetBorderSize(0)
    legend.SetFillStyle(0)
    legend.SetTextSize(0.035)
    legend.SetTextFont(42)

    stack = ROOT.THStack("hs", "")
    h_mc_tot = None # Questo terrà la somma totale di FONDI + SEGNALE per l'errore statistico

    # 3. Aggiungiamo i Fondi
    for fondo in FONDI:
        h_fondo = get_histogram(fondo["id"], HISTO_NAME)
        if h_fondo:
            h_fondo.SetFillColor(fondo["colore"])
            h_fondo.SetFillStyle(1001)
            h_fondo.SetLineColor(ROOT.kBlack)
            h_fondo.SetLineWidth(1)
            stack.Add(h_fondo)
            legend.AddEntry(h_fondo, f"{fondo['nome']}", "f")
            
            # Sommiamo al Monte Carlo totale
            if h_mc_tot is None:
                h_mc_tot = h_fondo.Clone("h_mc_tot")
            else:
                h_mc_tot.Add(h_fondo)

    # 4. Aggiungiamo i Segnali
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
        stack.Add(h_segnale_tot) 
        legend.AddEntry(h_segnale_tot, "Higgs (125 GeV)", "f")
        
        # Aggiungiamo il segnale al Monte Carlo totale
        if h_mc_tot:
            h_mc_tot.Add(h_segnale_tot)

    # 5. Aggiungiamo i Dati veri
    h_dati_tot = None
    for data_dir in DATI:
        h_d = get_histogram(data_dir, HISTO_NAME)
        if h_d:
            if h_dati_tot is None:
                h_dati_tot = h_d.Clone("h_dati_tot")
            else:
                h_dati_tot.Add(h_d)
                
    if h_dati_tot:
        h_dati_tot.SetMarkerStyle(20) 
        h_dati_tot.SetMarkerSize(1.1)
        h_dati_tot.SetLineColor(ROOT.kBlack)
        legend.AddEntry(h_dati_tot, "Data 13 TeV", "pe")

    # 6. Disegniamo lo Stack
    stack.Draw("HIST")
    
    # Formattazione assi stack
    massimo_stack = stack.GetMaximum()
    massimo_dati = h_dati_tot.GetMaximum() if h_dati_tot else 0
    stack.SetMaximum(max(massimo_stack, massimo_dati) * 1.35) 
    stack.SetMinimum(0.01)
    
    if h_dati_tot:
        bin_width = h_dati_tot.GetXaxis().GetBinWidth(1)
        stack.GetYaxis().SetTitle(f"Events / {bin_width:.2f} GeV")
    else:
        stack.GetYaxis().SetTitle("Events")
        
    stack.GetYaxis().SetTitleSize(0.055)
    stack.GetYaxis().SetLabelSize(0.05)
    stack.GetXaxis().SetLabelSize(0) # Nascondiamo i numeri dell'asse X (sono nel ratio)
    stack.GetXaxis().SetRangeUser(80, 170)

    # 7. Disegniamo la BANDA DI INCERTEZZA STATISTICA (Sul MC Totale)
    if h_mc_tot:
        h_mc_tot.SetFillStyle(3254)  # Tratteggio
        h_mc_tot.SetFillColor(ROOT.kGray + 2)
        h_mc_tot.SetMarkerSize(0)
        h_mc_tot.Draw("E2 SAME")     # E2 = Disegna come banda
        legend.AddEntry(h_mc_tot, "Stat. Unc.", "f")

    # 8. Disegniamo i Dati sopra a tutto
    if h_dati_tot:
        h_dati_tot.Draw("PE1 SAME")

    legend.Draw("SAME")
    
    # Scritte ATLAS
    testo = ROOT.TLatex()
    testo.SetNDC()
    testo.SetTextFont(72)
    testo.SetTextSize(0.06)
    testo.DrawLatex(0.16, 0.84, "ATLAS")
    testo.SetTextFont(42)
    testo.DrawLatex(0.31, 0.84, "Open Data")
    testo.SetTextSize(0.045)
    testo.DrawLatex(0.16, 0.77, "#sqrt{s} = 13 TeV, 10 fb^{-1}")
    testo.DrawLatex(0.16, 0.71, "H #rightarrow ZZ* #rightarrow 4l")

    # ==========================================
    # PAD 2: RATIO PLOT (Dati / Monte Carlo)
    # ==========================================
    pad2.cd()
    
    if h_dati_tot and h_mc_tot:
        # Calcolo del rapporto Dati/MC
        h_ratio = h_dati_tot.Clone("h_ratio")
        h_ratio.Divide(h_mc_tot)
        
        # Formattazione grafica
        h_ratio.SetTitle("")
        h_ratio.GetYaxis().SetTitle("Data / MC")
        h_ratio.GetYaxis().SetRangeUser(0.0, 2.0)
        h_ratio.GetXaxis().SetRangeUser(80, 170)
        
        # Le scritte devono essere più grandi perché il pad è schiacciato
        h_ratio.GetYaxis().SetTitleSize(0.12)
        h_ratio.GetYaxis().SetTitleOffset(0.45)
        h_ratio.GetYaxis().SetLabelSize(0.1)
        h_ratio.GetYaxis().SetNdivisions(505)
        
        h_ratio.GetXaxis().SetTitle("m_{4l} [GeV]")
        h_ratio.GetXaxis().SetTitleSize(0.14)
        h_ratio.GetXaxis().SetTitleOffset(1.1)
        h_ratio.GetXaxis().SetLabelSize(0.12)
        
        # Creazione della banda di incertezza sul Ratio (attorno a 1.0)
        h_ratio_mc_err = h_mc_tot.Clone("h_ratio_mc_err")
        for i in range(1, h_ratio_mc_err.GetNbinsX() + 1):
            val = h_ratio_mc_err.GetBinContent(i)
            err = h_ratio_mc_err.GetBinError(i)
            if val > 0:
                h_ratio_mc_err.SetBinContent(i, 1.0)
                h_ratio_mc_err.SetBinError(i, err / val)
            else:
                h_ratio_mc_err.SetBinContent(i, 1.0)
                h_ratio_mc_err.SetBinError(i, 0.0)
                
        h_ratio_mc_err.SetFillStyle(3254)
        h_ratio_mc_err.SetFillColor(ROOT.kGray + 2)
        h_ratio_mc_err.SetMarkerSize(0)
        
        # Ordine di disegno: Sfondo Errore -> Linea a 1.0 -> Punti Dati
        h_ratio.Draw("AXIS")          
        h_ratio_mc_err.Draw("E2 SAME")
        
        # Recuperiamo i bordi esatti del grafico visibile per evitare che la linea sbordi
        xmin = h_ratio.GetXaxis().GetBinLowEdge(h_ratio.GetXaxis().GetFirst())
        xmax = h_ratio.GetXaxis().GetBinUpEdge(h_ratio.GetXaxis().GetLast())
        
        linea = ROOT.TLine(xmin, 1.0, xmax, 1.0)
        linea.SetLineColor(ROOT.kRed)
        linea.SetLineStyle(2)
        linea.SetLineWidth(2)
        linea.Draw("SAME")
        
        h_ratio.Draw("PE1 SAME")
        
        # Ridisegniamo la cornice nera sopra a tutto per "tagliare" eventuali sbavature
        pad2.RedrawAxis()
        
        # Facciamolo anche per il pad1 superiore per massima pulizia!
        pad1.cd()
        pad1.RedrawAxis()

    # ==========================================
    # SALVATAGGIO
    # ==========================================
    out_name = "Higgs_Discovery_Plot.png"
    canvas.SaveAs(out_name)
    canvas.SaveAs("Higgs_Discovery_Plot.pdf")
    print(f"\nGrafico completato e salvato come {out_name}!")

if __name__ == "__main__":
    main()