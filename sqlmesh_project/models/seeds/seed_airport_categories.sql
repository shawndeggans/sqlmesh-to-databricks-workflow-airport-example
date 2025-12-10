MODEL (
    name seeds.airport_categories,
    kind SEED (
        path '../../seeds/seed_airport_categories.csv'
    ),
    grain category_code
);
