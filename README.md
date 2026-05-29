# TrimSniper V.1.0.0

> **Nota:** Questa repository è una rielaborazione personalizzata di [Fh6-Sniper V1.0.1](https://github.com/FrostyIsBored/FH6-Auction-House-Sniper/tree/v1.0.1).

## Modifiche principali
* **Aggiunta compatibilità multi-risoluzione** (testate e funzionanti: 720p, 1080p, 2K e 4K)
* **Aggiunta compatibilità HDR** (se si usa l'HDR, è necessario abilitare l'opzione "sfondi animati" sia nella configurazione del bot che nel gioco)
* **Traduzione completa dello strumento in italiano**
* **Interfaccia utente personalizzata** (lavori in corso)

## Modifiche future
* Correggere l'incompatibilità tra HDR e sfondi animati
* Aggiungere compatibilità per risoluzioni personalizzate e rapporti d'aspetto non standard
* Aggiungere compatibilità per la lingua italiana nel gioco
* Correggere bug minori non funzionali
* Completare la personalizzazione dell'interfaccia utente

---

# FH6 Auction House Sniper

## Sniper automatico per la Casa d'aste di Forza Horizon 6

Monitora la Casa d'aste per l'auto impostata, la acquista immediatamente non appena appare, la riscuote e riparte in loop. Configura i filtri una sola volta e lascialo girare. Questo strumento ha un tasso di acquisto immediato di circa il 10% e in genere riesce a fare uno snipe in meno di 5 minuti.

<img width="1655" height="792" alt="image-3" src="https://github.com/user-attachments/assets/61b58048-c3e6-4156-9510-0c2600aa7e9f" />

---

# Funzionalità

- Ricerca e acquisto immediato automatici
- Salta gli annunci già venduti per trovarne uno nuovo
- Riscuote automaticamente ogni auto vinta
- Piccola overlay sempre in primo piano con statistiche in tempo reale
- F8 avvia/ferma, F9 stop di emergenza
- Stop automatico dopo un numero definito di auto o di minuti
- Riconoscimento intelligente della pagina per evitare clic accidentali su altre schermate

---

# Requisiti e settaggi

- Windows 10 o 11
- Forza Horizon 6 su PC
- Risoluzione 4k/2k/1080p/720p – NO HDR - Schermo intero, frame rate sbloccato - dimensione HUD 100%
- Preset grafico Molto basso
- Sfondo animato (Accesivibilità visive) **Disattivato**
- HDR (OPZIONALE)(AUMENTA IMPUT LAG) - Sfondo animato **Attivato** - in config.json "moving_bg" **true**
- Lingua del gioco impostata su **English (US)**
- Connessione Ethernet cablata fortemente consigliata

<img width="1386" height="763" alt="image-4" src="https://github.com/user-attachments/assets/fd2bf173-259f-4458-938b-2267144ce3ab" />
<img width="1386" height="758" alt="image-5" src="https://github.com/user-attachments/assets/34f3fe88-9575-4ec5-aa6c-0c9e04a9964c" />

---

# Download

Scarica l'ultima versione di **TrimSniper.zip** dalla [pagina Releases](https://github.com/d1ablo4L/TrimSniper/releases) ed estraila in qualsiasi cartella del tuo PC.

---

# Configurazione

## Passo 1 – Apri la Casa d'aste

Avvia Forza Horizon 6 e vai alla Casa d'aste nel sito del festival.

<img width="1916" height="971" alt="image-1" src="https://github.com/user-attachments/assets/2e4c412e-974e-4bf4-9d4d-bbc31fcd2432" />

---

## Passo 2 – Configura la ricerca

Apri **Cerca aste** e imposta i filtri:

- **Marca** e **Modello** dell'auto che vuoi
- **Prezzo massimo di acquisto immediato** come limite di sicurezza. Il bot acquista la prima auto corrispondente senza controllare il prezzo, quindi questo è il massimo che puoi spendere per auto. Impostalo con attenzione.

Torna indietro in modo che la schermata mostri la **visualizzazione configurazione ricerca**. È lì che il bot si aspetta di iniziare.

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7fac68c0-f89d-45ee-a10a-5133b02da681" />

---

## Passo 3 – Avvia lo sniper

Fai doppio clic su **TrimSniper.exe**. Apparirà una piccola overlay nell'angolo in alto a sinistra dello schermo.

Torna su FH6, premi **F8** o **Avvia**, e lascialo girare.

Per fermare: premi di nuovo **F8**, **F9** per lo stop di emergenza, oppure clicca **STOP** sull'overlay.

<img width="1902" height="1062" alt="image-2" src="https://github.com/user-attachments/assets/ccdfba46-4c90-42de-bb79-fe26658bb262" />

---

# Avviso SmartScreen

Windows SmartScreen mostrerà un avviso perché l'exe non è firmato digitalmente. Per eseguirlo comunque:

1. Clicca su **Ulteriori informazioni**
2. Clicca su **Esegui comunque**

---

# Tasti rapidi

| Tasto | Azione |
|---|---|
| **F8** | Avvia / ferma |
| **F9** | Stop di emergenza |
| Pulsante **STOP** | Come F8 |
| **✕** sull'overlay | Chiudi ed esci |

---

# Impostazioni aggiuntive 

Il bot è pronto all'uso senza modifiche. Se vuoi personalizzarlo, apri **config.json** (creato nella stessa cartella dell'exe al primo avvio):

- **max_cars** – stop automatico dopo questo numero di vittorie (predefinito: 1)
- **max_minutes** – stop automatico dopo questi minuti (predefinito: 180)
- **collect_after_buyout** – imposta su `false` se preferisci riscuotere le auto manualmente
- **notify_sound** / **notify_toast** – disattiva il segnale sonoro o la notifica toast alla vittoria
- **buyout_select_delay_ms** – millisecondi aggiuntivi tra la selezione di Acquisto immediato e la pressione di Invio. Imposta a `200` se il bot apre occasionalmente la finestra Fai un'offerta invece di Acquisto immediato (predefinito: 0)
- **moving_background** – imposta su `false` se l'opzione sfondo animato di FH6 è **disattivata** (per HDR impostare: true)

---

# Importante

> [!WARNING]
> - L'automazione della Casa d'aste potrebbe violare le Linee guida di condotta di Forza.
> - I risultati possono variare in base alla configurazione del PC e della rete.
> - Si rischia un avviso, una sospensione o un ban permanente.
> - Usalo a tuo rischio e pericolo.

---

# Note

- Il bot funziona solo mentre FH6 è la finestra attiva. L'overlay mostra **In pausa** se passi ad un'altra finestra. Clicca di nuovo sul gioco per riprendere.
- L'overlay è nascosta dalle acquisizioni schermo, quindi puoi lasciarla ovunque sullo schermo.
- Trascina l'overlay cliccando e tenendo premuta la barra del titolo.
- Non vincerai ogni snipe. Il bot è limitato dalle animazioni dei menu di FH6 e dalla risposta del server delle aste, come qualsiasi altro strumento.
- Se i server sono lenti o sovraccarichi, il bot potrebbe smettere di funzionare correttamente (una correzione è in arrivo a breve).

---

# Risoluzione dei problemi

**L'overlay mostra "In pausa"** – FH6 non è la finestra attiva. Clicca sul gioco.

**F8 non fa nulla** – un'altra applicazione sul tuo PC potrebbe intercettare il tasto F8. Chiudila, oppure cambia il tasto rapido in `config.json`.

**Il bot si perde in una schermata e rimane bloccato** – riavvia FH6 e il bot. Assicurati che il preset grafico sia **Molto basso** e la risoluzione **1920 x 1080**.

**Quando segnali problemi relativi al bot** – includi il file Sniper.log in modo che possa analizzarlo. Se il problema persiste, [apri una segnalazione](https://github.com/d1ablo4L/TrimSniper/issues) o contattami su Discord "d1ablo4l".
