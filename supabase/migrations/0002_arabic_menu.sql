-- Arabic text for menu items. Prices, allergens and diets stay single-sourced.
-- Safe to run repeatedly.
alter table app.menu_items add column if not exists name_ar text not null default '';
alter table app.menu_items add column if not exists description_ar text not null default '';
alter table app.menu_items add column if not exists ingredients_ar text[] not null default '{}';
