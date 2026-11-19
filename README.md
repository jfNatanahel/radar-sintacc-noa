# Radar Sin TACC · NOA

![tests](https://github.com/jfNatanahel/radar-sintacc-noa/actions/workflows/tests.yml/badge.svg)

Inteligencia competitiva para insumos sin TACC en Salta, Jujuy y La Rioja. Cruza los precios de insumos de Mercado Libre con la oferta sin TACC de los locales gastronómicos en Google Maps.

Capstone del Samsung Innovation Campus 2026 · Equipo DataPatitos: Valentina (BIZ), Jose (DS) y Natanahel (SE).

## Flujo

```
Make (programado) ──> Actor de Apify  {operation: "analytics" | "inference"}
                        └─> key-value store `radar-sintacc` ──> Google Sheets ──> AppSheet (dashboard)
```

| Producto | Operación | Estado |
|---|---|---|
| 1 · Analytics: de los datos a la información | `analytics` | Entregado el 17/11 |
| 2 · Inference: de la información a las decisiones | `inference` | En desarrollo |

## Estructura del repo

```
sintacc-actor/   el Actor de Apify (código, tests y README con input, output y decisiones de datos)
docs/            lineamientos.md: cumplimiento de las reglas R1 a R4 del Actor
.github/         tests automáticos en cada push (GitHub Actions)
```

El build de Apify apunta a la carpeta `sintacc-actor` (`#main:sintacc-actor`).

## Empezar

Ver [`sintacc-actor/README.md`](sintacc-actor/README.md).
