#!/usr/bin/env python3
import argparse
import math
import os
import re
import shutil
import sys

try:
    import ROOT
except Exception as e:
    print('ERRORE: PyROOT è necessario per eseguire questo script.')
    print(e)
    sys.exit(1)

ROOT.gROOT.SetBatch(True)
ROOT.TH1.SetDefaultSumw2(True)

def find_first_tree(root_dir):
    for key in root_dir.GetListOfKeys():
        obj = key.ReadObj()
        if obj.InheritsFrom('TTree'):
            return obj
        if obj.InheritsFrom('TDirectory'):
            tree = find_first_tree(obj)
            if tree:
                return tree
    return None

def branch_names(tree):
    return {b.GetName() for b in tree.GetListOfBranches()}

def get_event_weight(tree, branches, is_data=False):
    if is_data:
        return 1.0
    w = 1.0
    if 'mcWeight' in branches:
        w *= float(tree.mcWeight)
    for b_name in branches:
        if b_name.startswith('scaleFactor_'):
            w *= float(getattr(tree, b_name))
    return w

def to_list(x):
    if x is None: return []
    try: return list(x)
    except TypeError: return [x]

def get_collection(tree, name, branches):
    if name not in branches: return []
    try: return to_list(getattr(tree, name))
    except Exception: return []

def build_lepton_p4(pt_gev, eta, phi, mass_gev=0.0):
    v = ROOT.TLorentzVector()
    v.SetPtEtaPhiM(pt_gev, eta, phi, mass_gev)
    return v

def check_deltaR_and_low_mass_veto(good_leptons, lep_p4_dict, lep_type, lep_charge):
    for i in range(len(good_leptons)):
        for j in range(i+1, len(good_leptons)):
            idx_i = good_leptons[i]
            idx_j = good_leptons[j]
            p4_i = lep_p4_dict[idx_i]
            p4_j = lep_p4_dict[idx_j]
            
            # Taglio DeltaR > 0.10 per tutte le coppie di leptoni (come da appunti/articolo)
            if p4_i.DeltaR(p4_j) < 0.10:
                return False
            
            # Low Mass Veto: m_ll > 5 GeV per coppie SFOS
            is_sf = (lep_type[idx_i] == lep_type[idx_j])
            is_os = ((lep_charge[idx_i] * lep_charge[idx_j]) < 0)
            if is_sf and is_os:
                if (p4_i + p4_j).M() < 5.0:
                    return False
    return True

def find_z_pairs(indices, lep_type, lep_charge, lep_p4):
    M_Z = 91.1876
    pairs = []
    
    for j in range(len(indices)):
        for k in range(j+1, len(indices)):
            i, j_idx = indices[j], indices[k]
            if lep_type[i] == lep_type[j_idx] and (lep_charge[i] * lep_charge[j_idx]) < 0:
                mass = (lep_p4[i] + lep_p4[j_idx]).M()
                pairs.append((i, j_idx, mass))
    
    if len(pairs) < 2:
        return None
    
    best_config = None
    best_score = float('inf')
    
    for idx1 in range(len(pairs)):
        for idx2 in range(idx1+1, len(pairs)):
            i1, i2, m1 = pairs[idx1]
            i3, i4, m2 = pairs[idx2]
            
            if len({i1, i2, i3, i4}) == 4:
                dist1 = abs(m1 - M_Z)
                dist2 = abs(m2 - M_Z)
                
                # Z1 è la coppia più vicina alla massa nominale
                if dist1 < dist2:
                    current_score = dist1
                    config = (i1, i2, i3, i4)
                else:
                    current_score = dist2
                    config = (i3, i4, i1, i2)
                
                if current_score < best_score:
                    best_score = current_score
                    best_config = config
                    
    return best_config

def make_hists():
    h = {}
    labels = [
        '1. All events', 
        '2. == 4 good lep', 
        '3. Trigger pT', 
        '4. dR & LowMass Veto',
        '5. SFOS Paired',
        '6. Z1 Mass Cut',
        '7. Z2 Mass Cut',
        '8. Higgs Mass Window'
    ]
    h['cutflow'] = ROOT.TH1F('cutflow', 'Event Selection Cutflow;Selection Step;Events', len(labels), 0.5, len(labels) + 0.5)
    for i, lab in enumerate(labels, start=1):
        h['cutflow'].GetXaxis().SetBinLabel(i, lab)

    h['nlep'] = ROOT.TH1F('nlep', 'Lepton multiplicity;N_{lep};Events', 8, -0.5, 7.5)
    h['lead_lep_pt'] = ROOT.TH1F('lead_lep_pt', 'Leading lepton p_{T};p_{T}^{lead} [GeV];Events', 50, 0.0, 300.0)
    h['m_Z1'] = ROOT.TH1F('m_Z1', 'Z1 invariant mass;m_{Z1} [GeV];Events', 60, 40.0, 120.0)
    h['m_Z2'] = ROOT.TH1F('m_Z2', 'Z2 invariant mass;m_{Z2} [GeV];Events', 60, 10.0, 120.0)
    # Range esteso per vedere le code come da appunti
    h['m_Higgs'] = ROOT.TH1F('m_Higgs', 'Higgs invariant mass;m_{4l} [GeV];Events', 16, 110.0, 160.0)
    return h

def save_hists(hists, outdir, is_data):
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)
    fout = ROOT.TFile(os.path.join(outdir, 'analysis_histograms.root'), 'RECREATE')
    for hist in hists.values(): 
        hist.Write()
    fout.Close()

    canvas = ROOT.TCanvas('canvas', 'Analisi Higgs', 800, 600)
    for name, hist in hists.items():
        canvas.Clear()
        
        if is_data:
            hist.SetMarkerStyle(20)
            hist.SetMarkerSize(1.2)
            hist.SetLineColor(ROOT.kBlack)
            draw_opt = 'PE1'
        else:
            hist.SetLineColor(ROOT.kBlue + 2)
            hist.SetLineWidth(2)
            hist.SetFillColor(ROOT.kAzure + 7)
            draw_opt = 'HIST'
        
        if name == 'cutflow':
            hist.LabelsOption('v', 'X')
            canvas.SetBottomMargin(0.35) 
            hist.Draw(draw_opt)
            if not is_data:
                hist.SetMarkerSize(1.5)
                hist.Draw('HIST TEXT0 SAME') 
        else:
            canvas.SetBottomMargin(0.15)
            hist.GetXaxis().SetTitleOffset(1.2)
            hist.GetYaxis().SetTitleOffset(1.3)
            hist.Draw(draw_opt)
            
        canvas.SaveAs(os.path.join(outdir, f'{name}.png'))

def main():
    parser = argparse.ArgumentParser(description='Analisi H->ZZ->4l ATLAS')
    parser.add_argument('input', help='Input ROOT file')
    parser.add_argument('-o', '--outdir', default=None)
    parser.add_argument('--lumi', type=float, default=10000.0, help='Luminosita integrata in pb^-1')
    args = parser.parse_args()

    # Estrai solo il nome del file (es. "mc_345060.root") ignorando il percorso
    input_name = os.path.basename(args.input)
    
    if args.outdir is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_root = os.path.join(project_root, 'output')
        os.makedirs(output_root, exist_ok=True)

        match = re.search(r'mc_(\d+)', input_name)
        if match:
            args.outdir = os.path.join(output_root, f'analysis_output_{match.group(1)}')
        else:
            data_match = re.search(r'data[_-]?([A-Za-z0-9]+)', input_name, re.IGNORECASE)
            if data_match:
                suffix = data_match.group(1)
                args.outdir = os.path.join(output_root, f'output_data_{suffix}')
            else:
                args.outdir = os.path.join(output_root, 'analysis_output')

    # Apri il file e cerca l'albero (queste righe non cambiano)
    f = ROOT.TFile.Open(args.input)
    tree = find_first_tree(f)
    
    # Cerca la parola 'data' all'interno di input_name (il nome pulito), non in args.input!
    is_data = 'data' in input_name.lower()
    
    branches = branch_names(tree)
    h = make_hists()
    nentries = tree.GetEntries()

    print(f"Inizio processamento di {nentries} eventi...")

    for i, event in enumerate(tree):
        if i and i % 50000 == 0: print(f'  ... processati {i} / {nentries}')

        w = get_event_weight(tree, branches, is_data=is_data)
        h['cutflow'].Fill(1, w)

        lep_pt = get_collection(tree, 'lep_pt', branches)
        lep_eta = get_collection(tree, 'lep_eta', branches)
        lep_phi = get_collection(tree, 'lep_phi', branches)
        lep_charge = get_collection(tree, 'lep_charge', branches)
        lep_type = get_collection(tree, 'lep_type', branches)
        # lep_ptcone30 = get_collection(tree, 'lep_ptcone30', branches)
        # lep_etcone20 = get_collection(tree, 'lep_etcone20', branches)
        
        # Estrazione della variabile del parametro d'impatto (se esiste nell'entupla)
        lep_trksigd0unbiased = get_collection(tree, 'lep_trksigd0unbiased', branches)
        lep_trkd0unbiased = get_collection(tree, 'lep_trkd0unbiased', branches)

        raw_nlep = len(lep_pt)
        
        # =============================================================
        # OBJECT SELECTION (Definizione dei Leptoni di Analisi)
        # =============================================================
        good_leptons = []
        lep_p4_dict = {}

        for j in range(raw_nlep):
            pt_gev = lep_pt[j] / 1000.0 
            eta = lep_eta[j]
            l_type = abs(lep_type[j]) 
            
            # Kinematics
            if l_type == 11 and pt_gev < 7.0: continue
            if l_type == 13 and pt_gev < 5.0: continue
            if l_type == 11 and abs(eta) > 2.47: continue
            if l_type == 13 and abs(eta) > 2.7: continue
            
            # Isolation
            # rel_pt_iso = lep_ptcone30[j] / lep_pt[j] if lep_pt[j] > 0 else 99
            # rel_et_iso = lep_etcone20[j] / lep_pt[j] if lep_pt[j] > 0 else 99
            # if rel_pt_iso > 0.15 or rel_et_iso > 0.15: 
                # continue
                
            # Impact Parameter Significance Cut (|d0|/sigma(d0))
            if len(lep_trksigd0unbiased) > j:
                # L'articolo richiede < 3 per muoni e < 5 per elettroni.
                if l_type == 11 and abs(lep_trkd0unbiased)/lep_trksigd0unbiased >= 5.0: continue
                if l_type == 13 and abs(lep_trkd0unbiased)/lep_trksigd0unbiased >= 3.0: continue

            good_leptons.append(j)
            mass_gev = 0.1056 if l_type == 13 else 0.000511
            lep_p4_dict[j] = build_lepton_p4(pt_gev, eta, lep_phi[j], mass_gev)

        h['nlep'].Fill(len(good_leptons), w)

        # =============================================================
        # EVENT SELECTION (Cutflow Region)
        # =============================================================
        
        # Cut 1: Molteplicità (Esattamente 4 come da appunti)
        if len(good_leptons) != 4: continue
        h['cutflow'].Fill(2, w)

        # Cut 2: Trigger pT matching (20, 15, 10 GeV)
        good_leptons.sort(key=lambda idx: lep_p4_dict[idx].Pt(), reverse=True)
        if lep_p4_dict[good_leptons[0]].Pt() < 20.0: continue
        if lep_p4_dict[good_leptons[1]].Pt() < 15.0: continue
        if lep_p4_dict[good_leptons[2]].Pt() < 10.0: continue
        h['cutflow'].Fill(3, w)

        # Cut 3: Delta R e Low Mass Veto
        if not check_deltaR_and_low_mass_veto(good_leptons, lep_p4_dict, lep_type, lep_charge):
            continue
        h['cutflow'].Fill(4, w)

        # Cut 4: Ricerca candidati Z (2 x OSSF)
        z_pair = find_z_pairs(good_leptons, lep_type, lep_charge, lep_p4_dict)
        if z_pair is None: continue
        h['cutflow'].Fill(5, w)
        
        j1, j2, j3, j4 = z_pair 
        z1_4v = lep_p4_dict[j1] + lep_p4_dict[j2]
        z2_4v = lep_p4_dict[j3] + lep_p4_dict[j4]
        h4_4v = z1_4v + z2_4v
        
        m_z1 = z1_4v.M() 
        m_z2 = z2_4v.M() 
        m_h = h4_4v.M()  
        
        # Cut 5: Massa Z1 (50 - 106 GeV)
        if m_z1 < 50.0 or m_z1 > 106.0:
            continue
        h['cutflow'].Fill(6, w)
        
        # Cut 6: Massa Z2 dinamica (sliding cut)
        # La soglia minima varia linearmente da 12 a 50 GeV se m_h è tra 140 e 190 GeV
        if m_h < 140.0:
            m_z2_min = 12.0
        elif m_h < 190.0:
            m_z2_min = 12.0 + (50.0 - 12.0) * (m_h - 140.0) / (190.0 - 140.0)
        else:
            m_z2_min = 50.0

        if m_z2 < m_z2_min or m_z2 > 115.0:
            continue
        h['cutflow'].Fill(7, w)
        
        # Cut 7: Finestra Massa Higgs (105 - 160 GeV come da appunti)
        if m_h < 105.0 or m_h > 160.0:
            continue
        h['cutflow'].Fill(8, w)

        # =============================================================
        # SIGNAL REGION: Riempimento Istogrammi
        # =============================================================
        h['lead_lep_pt'].Fill(lep_p4_dict[good_leptons[0]].Pt(), w)
        h['m_Z1'].Fill(m_z1, w)
        h['m_Z2'].Fill(m_z2, w)
        h['m_Higgs'].Fill(m_h, w)

    # =============================================================
    # NORMALIZZAZIONE MONTE CARLO
    # =============================================================
    if not is_data:
        tree.GetEntry(0)
        xsec = getattr(tree, 'XSection', 1.0)
        sumw = getattr(tree, 'SumWeights', 1.0)
        
        print(f"Normalizzazione MC: XSection = {xsec} pb, SumWeights = {sumw}, Lumi = {args.lumi} pb^-1")
        
        scale_factor = (args.lumi * xsec) / sumw
        for name, hist in h.items():
            hist.Scale(scale_factor)
            
    save_hists(h, args.outdir, is_data)
    print(f'Analisi completata. Output salvato in: {args.outdir}')

if __name__ == '__main__':
    main()