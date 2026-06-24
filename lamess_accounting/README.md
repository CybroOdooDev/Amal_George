# Lamess Accounting

## Scopo

Modulo dedicato a payout, ritenute e integrazione contabile.

## Ambito previsto

- workflow di payout
- logica di withholding
- integrazione fiscale/contabile
- contabilizzazione delle commissioni

## Stato attuale

Solo scheletro foundation.

## Dipendenze previste

- `account`
- `lamess_commission`

## Note

Questo modulo deve restare downstream rispetto al motore commissionale e non
deve ospitare UI portal o logica dell'albero rete.

## Installazione rapida

Esempio:

```bash
odoo-bin -d <db> -u lamess_accounting --stop-after-init
```
