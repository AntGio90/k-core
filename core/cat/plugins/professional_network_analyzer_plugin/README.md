# Professional Network Analyzer Plugin

Un plugin avanzato per Cheshire Cat AI che implementa funzionalità complete di analisi di reti professionali, mappatura delle competenze e identificazione di relazioni aziendali.

## 🎯 Caso d'Uso

Questo plugin è progettato per implementare il seguente scenario:

> **Use case scenario**: quando individuo un profilo, un nome, un job title o una competenza specifica, voglio poter ottenere informazioni sulle persone connesse a quel profilo (ad esempio colleghi, collaboratori o membri dello stesso team), inclusa la loro localizzazione geografica o aziendale. Voglio inoltre la possibilità di eseguire azioni simili, come esplorare la rete professionale di una persona, mappare le competenze associate e identificare i contesti lavorativi in cui queste relazioni si sviluppano.

## ⚡ Funzionalità Principali

### 🔍 Analisi Profili Professionali
- **Input**: Nome, job title o azienda
- **Output**: Informazioni dettagliate su profilo, competenze, team, location
- **Tool**: `analyze_professional_profile()`

### 🕸️ Esplorazione Rete Professionale  
- **Input**: Nome completo della persona
- **Output**: Mappa completa delle connessioni professionali
- **Tool**: `explore_professional_network()`

### 🏢 Mappatura Rete Aziendale
- **Input**: Nome dell'azienda
- **Output**: Struttura organizzativa, dipartimenti, sedi
- **Tool**: `map_company_network()`

### 🎯 Analisi Rete Competenze
- **Input**: Nome della competenza/skill
- **Output**: Network di persone con quella competenza
- **Tool**: `analyze_skill_network()`

### 📋 Identificazione Contesti Lavorativi
- **Input**: Descrizione di contesto, progetto o situazione
- **Output**: Progetti correlati, team, competenze
- **Tool**: `identify_work_context()`

## 🚀 Installazione

### 1. Installazione Rapida
```bash
# Estrai il ZIP nella cartella plugins del tuo Cheshire Cat
unzip professional_network_analyzer_plugin.zip -d /path/to/cheshire-cat/plugins/professional_network_analyzer/
```

### 2. Attiva il plugin
1. Vai al pannello Admin di Cheshire Cat (localhost:1865/admin)
2. Naviga nella sezione "Plugins" 
3. Trova "Professional Network Analyzer" nella lista
4. Clicca su "Activate"

### 3. Verifica l'installazione
Prova uno dei comandi nell'interfaccia chat:
```
Analizza il profilo di Mario Rossi
```

## 💬 Esempi di Utilizzo

### Analizzare un Profilo
```
Utente: "Dimmi tutto su Mario Rossi"
Cat: Analizza il profilo completo con competenze, team e connessioni
```

### Esplorare una Rete Professionale
```
Utente: "Esplora la rete professionale di Laura Bianchi" 
Cat: Mostra connessioni dirette, analisi team e competenze condivise
```

### Mappare un'Azienda
```
Utente: "Mappa la struttura di TechCorp Italia"
Cat: Visualizza organizzazione, dipartimenti e membri
```

### Analizzare Competenze
```
Utente: "Chi conosce Python nella mia rete?"
Cat: Lista esperti Python con dettagli e competenze correlate
```

### Identificare Contesti
```
Utente: "Dimmi dei progetti di machine learning"
Cat: Trova progetti, team e persone coinvolte
```

## 🛠️ Configurazione

Il plugin include un sistema di settings configurabile:

```json
{
  "enable_detailed_analysis": true,
  "include_geographic_data": true, 
  "max_network_depth": 3
}
```

## 📊 Struttura Dati

### Profili Professionali
```python
{
    "name": "Nome Cognome",
    "position": "Job Title", 
    "company": "Nome Azienda",
    "location": "Città, Paese",
    "skills": ["Competenza1", "Competenza2"],
    "experience_years": 5,
    "team": "Nome Team",
    "colleagues": ["Collega1", "Collega2"],
    "projects": ["Progetto1", "Progetto2"]
}
```

## 🔧 Personalizzazione

### Sostituire i Dati di Esempio
Modifica le strutture dati in `professional_network_analyzer.py`:

```python
SAMPLE_PROFILES = {
    "tuo_profilo": {
        "name": "Il Tuo Nome",
        "position": "La Tua Posizione",
        # ... altri dettagli
    }
}
```

### Aggiungere Nuovi Tool
```python
@tool(return_direct=True)
def il_mio_nuovo_tool(input_parameter, cat):
    """Descrizione del nuovo tool."""
    # La tua logica qui
    return "Risultato del tool"
```

## 🔒 Privacy e Sicurezza

- Il plugin gestisce informazioni professionali sensibili
- Assicurati di rispettare le normative sulla privacy (GDPR)
- Implementa controlli di accesso appropriati per uso aziendale
- Considera l'anonimizzazione per dati demo

## 🐛 Risoluzione Problemi

### Plugin non si attiva
- Verifica che i file siano nella cartella corretta
- Controlla la sintassi di `plugin.json`
- Riavvia Cheshire Cat

### Tool non funzionano
- Verifica che i decorator `@tool` siano corretti
- Controlla i log per errori Python
- Valida i parametri di input

## 🤝 Supporto

- **GitHub Issues**: Apri un issue per problemi o suggerimenti
- **Discord Community**: [Cheshire Cat AI Discord](https://discord.gg/bHX5sNFCYU)
- **Documentation**: [Cheshire Cat Docs](https://cheshire-cat-ai.github.io/docs/)

---

**Sviluppato con ❤️ per la Community di Cheshire Cat AI**
