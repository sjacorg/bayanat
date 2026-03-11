ALTER TABLE label ADD CONSTRAINT label_no_self_parent CHECK (parent_label_id != id);
ALTER TABLE label ADD CONSTRAINT label_unique_sibling_title UNIQUE (title, parent_label_id);
