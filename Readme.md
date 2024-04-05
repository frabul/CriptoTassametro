# Italiano
CriptoTassametro è una libreria python per calcolare il capital gain derivante dalle cripto-attività seguendo la normativa italiana
La classe CriptoTassametro può processare una lista di operazioni che includa delle istanze delle classi che ereditano da Components.Operation
Nella libreria è incluso BinanceHistoryParser che serve per generare suddetta lista a partire dalla storia transazioni fornita da Binance.
Al fine di eseguire un calcolo esatto è essenziale fornire un portafoglio di partenza corretto e con i costi di carico esatti.
## Note
- Non sono supportate le operazioni di staking e di prestito di cripto-attività.
- Non sono considerate soggette a tassazione le operazioni di acquisto e vendita crito-cripto, ma solo quelle crito-euro.


# English
A python library to calculate capital gain from "cripto-attività" 
CriptoTassametro is a Python library for calculating the capital gain derived from crypto-assets following Italian law.
The CryptoTaximeter class can process a list of operations that include instances of classes inheriting from Components.Operation.
The library includes BinanceHistoryParser, which is used to generate the aforementioned list from transaction history provided by Binance.
To perform an accurate calculation, it is essential to provide a correct initial portfolio with exact loading costs.
## Notes
- Staking and crypto-asset lending operations are not supported.
- Only crypto-euro operations are subject to taxation, not crypto-crypto operations.
