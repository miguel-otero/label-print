-- Additive and idempotent: historical jobs retain NULL (unknown modality).
alter table print_history add column if not exists prints_barcode boolean;
alter table print_batch_items add column if not exists prints_barcode boolean;
