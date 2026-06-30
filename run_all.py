#!/usr/bin/env python3
import os
import glob
import subprocess
import datetime

# ==========================================
# CONFIGURAZIONE (Modifica se necessario)
# ==========================================
CARTELLA_DATI = "data"
SCRIPT_ANALISI = "scripts/analyze4.py"
FILE_LOG = "analisi_batch.log"
# ==========================================

def main():
    # Trova tutti i file .root nella cartella dati
    pattern = os.path.join(CARTELLA_DATI, "*.root")
    root_files = glob.glob(pattern)

    if not root_files:
        print(f"Nessun file .root trovato nella cartella '{CARTELLA_DATI}'.")
        return

    print(f"Trovati {len(root_files)} file da processare. Inizio analisi...")
    
    # Apriamo il file di log in modalità scrittura ('w')
    with open(FILE_LOG, "w") as log:
        # Intestazione del log
        log.write(f"=== RUN DI ANALISI BATCH ===\n")
        log.write(f"Data e ora inizio: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"File processati: {len(root_files)}\n")
        log.write("=" * 40 + "\n\n")

        # Ciclo su tutti i file trovati
        for i, filepath in enumerate(root_files, start=1):
            nome_file = os.path.basename(filepath)
            orario = datetime.datetime.now().strftime('%H:%M:%S')
            
            print(f"[{i}/{len(root_files)}] Analizzando: {nome_file} ...", end=" ", flush=True)
            
            log.write(f"[{orario}] Processando: {nome_file}\n")
            log.write(f"Path: {filepath}\n")

            # Costruiamo il comando da lanciare sul terminale
            # Es: python3 scripts/analyze.py data/mc_345060.root
            comando = ["python3", SCRIPT_ANALISI, filepath]

            try:
                # subprocess.run esegue il comando e cattura l'output
                risultato = subprocess.run(comando, capture_output=True, text=True)
                
                # Scriviamo l'output (i "print" del tuo script) nel log
                log.write("--- OUTPUT ANALISI ---\n")
                if risultato.stdout:
                    log.write(risultato.stdout)
                
                # Se c'è stato un errore (es. ROOT crasha), lo scriviamo
                if risultato.stderr:
                    log.write("\n--- AVVISI / ERRORI ---\n")
                    log.write(risultato.stderr)
                
                # Controlliamo se ha finito con successo (codice 0)
                if risultato.returncode == 0:
                    print("Completato!")
                    log.write(f"Stato: SUCCESSO (Codice {risultato.returncode})\n")
                else:
                    print("ERRORE! (Vedi log)")
                    log.write(f"Stato: FALLITO (Codice {risultato.returncode})\n")

            except Exception as e:
                print("ERRORE CRITICO DI ESECUZIONE!")
                log.write(f"Errore di sistema nell'eseguire il file: {e}\n")
            
            log.write("-" * 40 + "\n\n")

        # Chiusura del log
        log.write(f"=== ANALISI TERMINATA ===\n")
        log.write(f"Data e ora fine: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    print(f"\nTutti i file sono stati processati!")
    print(f"I risultati sono nelle cartelle 'analysis_output_XXX'.")
    print(f"Puoi leggere i dettagli completi nel file '{FILE_LOG}'.")

if __name__ == "__main__":
    main()