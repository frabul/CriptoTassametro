# Italiano
CriptoTassametro è una libreria python per calcolare il capital gain derivante dalle cripto-attività seguendo la normativa italiana.
La classe CriptoTassametro può processare una qualsiasi lista di operazioni che includa delle istanze delle classi che si trovano in Components ed ereditano da Components.Operation,
Nella libreria è incluso BinanceHistoryParser che serve per generare suddetta lista a partire dalla storia transazioni fornita da Binance.
La storia di transazioni si può generare da Binance seguendo questa procedura: 
```
https://www.binance.com/en/support/faq/how-to-generate-transaction-history-990afa0a0a9341f78e7a9298a9575163
```
Al fine di eseguire un calcolo esatto è essenziale fornire un portafoglio di partenza corretto e con i costi di carico esatti.
## Per i profani
Per chi non è pratico di programmazione, è possibile utilizzare il file ParseAndCalculate.py per calcolare il capital gain a partire dalla storia delle transazioni fornita da Binance.
Per farlo è necessario:
1. Installare python
2. Installare le librerie richieste con il comando:
```
pip install -r requirements.txt
```
3. Ottenere la storia delle transazioni da Binance seguendo la procedura sopra indicata e salvarla in un file csv
4. Lanciare lo script ParseAndCalculate.py con il comando:
```
python ParseAndCalculate.py nome_sessione file_csv_da_processare

Esempio:
python ParseAndCalculate.py pippo history_di_pippo_2023.csv
```
## Note
- Non sono supportate le operazioni di staking e di prestito di cripto-attività.
- Non sono considerate soggette a tassazione le operazioni di acquisto e vendita crito-cripto, ma solo quelle crito-euro.

## Per donazioni :)
```
Ethereum o Binance Smart Chain: 0x4BF04e18e771Bc415ec3B92cb5D85eAdf98d96fa
```

# English
A python library to calculate capital gain from "cripto-attività" 
CriptoTassametro is a Python library for calculating the capital gain derived from crypto-assets following Italian law.
The CryptoTaximeter class can process a list of operations that include instances of classes found in Components and that inherit from Components.Operation.
The library includes BinanceHistoryParser, which is used to generate the aforementioned list from transaction history provided by Binance.
The transaction history can be generated from Binance by following this procedure:
```
https://www.binance.com/en/support/faq/how-to-generate-transaction-history-990afa0a0a9341f78e7a9298a9575163
```
To perform an accurate calculation, it is essential to provide a correct initial portfolio with exact loading costs.
## For non-programmers
For those who are not familiar with programming, it is possible to use the ParseAndCalculate.py file to calculate the capital gain from the transaction history provided by Binance.
To do this, you need to:
1. Install python
2. Install the required libraries with the command:
```
pip install -r requirements.txt
```
3. Obtain the transaction history from Binance by following the procedure above and save it in a csv file
4. Run the ParseAndCalculate.py script with the command:
```
python ParseAndCalculate.py session_name file_to_process

Example:
python ParseAndCalculate.py pippo pippo_history_2023.csv
```

## Notes
- Staking and crypto-asset lending operations are not supported.
- Only crypto-euro operations are subject to taxation, not crypto-crypto operations.


## Address for donations :)
```
Ethereum o Binance Smart Chain: 0x4BF04e18e771Bc415ec3B92cb5D85eAdf98d96fa
```
 