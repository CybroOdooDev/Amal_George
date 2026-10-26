## Module <pharmaceutical_base>

#### 20.06.2026
#### Version 19.0.1.0.0
#### ADD

- Initial commit for Pharmaceutical ERP

#### 30.07.2026
#### Version 19.0.1.1.0
#### ADD

- Storage-class routing for raw materials. Products declare the storage
  conditions they require via a new Storage Class field, locations declare the
  conditions they provide via the standard Storage Category, and putaway routes
  each move line to the matching warehouse sub-area.
- Enforce Storage Class setting. When enabled, transfers landing a classified
  material outside the area providing its storage class are refused, and a
  Storage Class becomes mandatory on pharmaceutical products. Off by default, so
  behaviour on existing databases is unchanged until the sub-areas are built.

#### FIX

- QC disposition transfers now resolve putaway on the move line, so a released
  cold-chain lot lands in the refrigerated sub-area of Released Stock instead of
  being pulled out of refrigeration the moment QA approves it.

#### 30.07.2026
#### Version 19.0.1.2.0
#### ADD

- Storage class on the traceability history. The Stock Moves smart button on the
  Quarantine Queue and the QC Test Order now shows the storage class each move
  went into, alongside the class the product requires, and the history can be
  grouped and filtered by storage class.

#### CHANGE

- The Quarantine Location and Released Stock Location settings are removed.
  Storage-class putaway is now the only location logic: receipts land on the
  warehouse's normal stock destination and putaway drops each line into the
  sub-area matching the product's Storage Class.
- Passing a QC test order no longer relocates material. The lot stays where
  putaway placed it and only its lot status changes to Approved.
- Failing a QC test order still segregates the lot into the Rejected Location,
  which remains configurable, with putaway resolved beneath it so a rejected
  cold-chain lot stays refrigerated.
