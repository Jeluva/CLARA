# ADR 0005 — Sentimiento: VADER para inglés, LLM para español (V2)

## Contexto
El BRIEF pide score de sentimiento por noticia y transcripción. VADER es
lexicón + reglas, pensado para inglés; en español financiero rinde flojo.

## Decisión
- Las noticias/transcripciones mock están en **inglés** (plausible para
  CEDEARs/US tickers y canales de research) y se puntúan con **VADER** de
  verdad: el `compound` ya viene normalizado a [-1, 1], que es nuestra
  convención. El sentimiento es **calculado, no hardcodeado**.
- Para **español financiero**, el camino de producción es un **LLM** con un
  prompt simple y barato. NO se implementa un VADER-en-español a medias.
- El score agregado por ticker es el promedio simple de sus noticias.

## Consecuencias
- (+) Pipeline de sentimiento real y demostrable hoy, sin red ni claves.
- (+) Decisión explícita y honesta sobre la limitación idiomática.
- (−) VADER es ingenuo al contexto financiero: titulares como "Nvidia *smashes*
  records on *insatiable* demand" pueden puntuar negativo porque el lexicón no
  entiende la jerga del mercado. Es exactamente la razón por la que el LLM es el
  camino real para V1 productivo. Queda anotado, no escondido.
