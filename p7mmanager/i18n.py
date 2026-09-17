# P7M Manager — inspect signed .p7m containers and extract what they carry
# Copyright (C) 2026 Marco Lombardo
#
# SPDX-License-Identifier: AGPL-3.0-or-later
# Distributed WITHOUT ANY WARRANTY; see LICENSE for the full terms.
# A commercial licence, without the AGPL's obligations, is available for use
# in proprietary or closed-source products — see COMMERCIAL-LICENSE.md.

"""English and Italian, from one table — the same mechanism Orion uses.

The code is written in English and translated into Italian by looking the
English up: :func:`tr` takes the string the source already contains and returns
the Italian for it, or the English back when the language is English or the
phrase has no translation yet. A test walks the source for every ``tr(...)``
call and fails on any phrase missing from the table, which is the check a
compiled ``.qm`` file cannot give.

The engine reports its own diagnostics in English too, and those arrive with a
variable tail — ``read failed: Permission denied``. :func:`tr_message` handles
that shape: it translates the fixed part before the colon and leaves the
system's own words alone, because a half-translated message is still clearer
than an untranslated one.
"""

from __future__ import annotations

import re
from enum import Enum

__all__ = ["Language", "current_language", "detect_language", "set_language", "tr",
           "tr_message", "TRANSLATIONS"]


class Language(str, Enum):
    ENGLISH = "en"
    ITALIAN = "it"

    @property
    def label(self) -> str:
        """The language's name in itself, which is how a picker should read."""
        return "Italiano" if self is Language.ITALIAN else "English"


def detect_language(locale_name: str | None) -> Language:
    """Italian for an Italian system, English for everything else."""
    if not locale_name:
        return Language.ENGLISH
    return Language.ITALIAN if locale_name.lower().startswith("it") else Language.ENGLISH


_language: Language = Language.ENGLISH


def set_language(language: Language) -> None:
    global _language
    _language = language


def current_language() -> Language:
    return _language


def tr(text: str) -> str:
    """Translate a source string, or hand it back unchanged."""
    if _language is Language.ENGLISH:
        return text
    return TRANSLATIONS.get(text, text)


# Engine messages that carry a number: the phrase is fixed, the count is not.
_COUNTED = (
    (re.compile(r"^(\d+) signatures$"), "{0} firme"),
    (re.compile(r"^(\d+) buste$"), "{0} buste"),
)


def tr_message(text: str) -> str:
    """Translate an engine message, whatever shape it arrives in.

    Three shapes occur, and all three are handled here rather than at each
    call site: the plain phrase, ``fixed part: detail`` where the detail comes
    from the operating system, and the summary line, which is several phrases
    joined with a middle dot and must be translated piece by piece.
    """
    if _language is Language.ENGLISH or not text:
        return text
    translated = TRANSLATIONS.get(text)
    if translated is not None:
        return translated
    if " · " in text:
        return " · ".join(tr_message(part) for part in text.split(" · "))
    for pattern, replacement in _COUNTED:
        match = pattern.match(text)
        if match:
            return replacement.format(*match.groups())
    if ": " in text:
        head, tail = text.split(": ", 1)
        head_translated = TRANSLATIONS.get(head)
        if head_translated is not None:
            return f"{head_translated}: {tail}"
    if " (" in text and text.endswith(")"):
        head, tail = text.split(" (", 1)
        head_translated = TRANSLATIONS.get(head)
        if head_translated is not None:
            return f"{head_translated} ({tail}"
    return text


# ---------------------------------------------------------------------
# English source string -> Italian
# ---------------------------------------------------------------------
TRANSLATIONS: dict[str, str] = {
    # -- engine: analysis and extraction messages ---------------------
    "detached signature: no document enclosed": "firma separata: nessun documento incluso",
    "detached signature: the signed document is not enclosed":
        "firma separata (detached): il documento firmato non è incluso",
    "detached signature: the document is not in the file":
        "firma separata: il documento non è nel file",
    "detached signature: nothing to extract": "firma separata: niente da estrarre",
    "nothing to verify: detached signature without signed attributes":
        "niente da verificare: firma separata senza attributi firmati",
    "recovered by scanning": "recuperato per scansione",
    "no extractable content": "nessun contenuto estraibile",
    "no content": "nessun contenuto",
    "empty file": "file vuoto",
    "1 signature": "1 firma",
    "content type not recognised": "tipo di contenuto non riconosciuto",
    "nested envelopes beyond the supported depth":
        "buste annidate oltre la profondità supportata",
    "the signer's certificate is not enclosed":
        "il certificato del firmatario non è incluso nella busta",
    "the signer's certificate is not in the file":
        "il certificato del firmatario non è presente nel file",
    "the counter-signature certificate is not enclosed":
        "il certificato della controfirma non è incluso",
    "the content does not match the signed digest":
        "il contenuto non corrisponde al digest firmato",
    "the signature does not match the signed data":
        "la firma non corrisponde ai dati firmati",
    "invalid RSA padding": "padding RSA non valido",
    "RSA-PSS: signature not verified by this tool":
        "RSA-PSS: firma non verificata da questo strumento",
    "DigestInfo unreadable": "DigestInfo illeggibile",
    "already there: skipped": "già presente: saltato",
    "cancelled": "annullato",
    "unknown": "sconosciuto",
    "(unknown)": "(sconosciuto)",
    "(unknown signer)": "(firmatario sconosciuto)",
    "invalid certificate": "certificato non valido",
    "empty ContentInfo": "ContentInfo vuoto",
    "empty SignerInfo": "SignerInfo vuoto",
    "SignedData missing": "SignedData assente",
    "SignedData incomplete": "SignedData incompleto",
    "ContentInfo without a contentType": "ContentInfo senza contentType",
    # messages whose detail is appended after a colon or in brackets
    "file not accessible": "file non accessibile",
    "read failed": "lettura non riuscita",
    "write failed": "scrittura non riuscita",
    "file too large": "file troppo grande",
    "destination folder unusable": "cartella di destinazione non utilizzabile",
    "unexpected error": "errore imprevisto",
    "invalid ASN.1 structure": "struttura ASN.1 non valida",
    "unreadable SignerInfo": "SignerInfo illeggibile",
    "CMS content is not signed data": "il contenuto CMS non è dati firmati",
    "too many files with the same name in the destination folder":
        "troppi file con lo stesso nome nella cartella di destinazione",
    # -- payload kinds -------------------------------------------------
    "PDF document": "Documento PDF",
    "XML document": "Documento XML",
    "ZIP archive": "Archivio ZIP",
    "Word document (OOXML)": "Documento Word (OOXML)",
    "Excel workbook (OOXML)": "Foglio Excel (OOXML)",
    "PowerPoint presentation (OOXML)": "Presentazione PowerPoint (OOXML)",
    "Office 97-2003 document": "Documento Office 97-2003",
    "RTF document": "Documento RTF",
    "PNG image": "Immagine PNG",
    "JPEG image": "Immagine JPEG",
    "TIFF image": "Immagine TIFF",
    "GIF image": "Immagine GIF",
    "7-Zip archive": "Archivio 7-Zip",
    "RAR archive": "Archivio RAR",
    "GZIP archive": "Archivio GZIP",
    "Nested signed envelope": "Busta firmata annidata",
    "Binary data": "Dati binari",
    "Text": "Testo",
    "Empty": "Vuoto",
    # -- menus ---------------------------------------------------------
    "&File": "&File",
    "&Add files…": "&Aggiungi file…",
    "Add &folder…": "Aggiungi &cartella…",
    "&Export report…": "&Esporta report…",
    "&Quit": "&Esci",
    "&Queue": "&Coda",
    "&Start": "&Avvia",
    "&Cancel": "&Annulla",
    "&Remove selected": "&Rimuovi selezionati",
    "Clear &completed": "Rimuovi &completati",
    "Clear &all": "Svuota &tutto",
    "&View": "&Visualizza",
    "&Language": "&Lingua",
    "&Help": "&?",
    "&About": "&Informazioni",
    # -- toolbar and buttons -------------------------------------------
    "Add files": "Aggiungi file",
    "Add folder": "Aggiungi cartella",
    "Start": "Avvia",
    "Cancel": "Annulla",
    "Remove": "Rimuovi",
    "Clear": "Svuota",
    "Open folder": "Apri cartella",
    "Open document": "Apri documento",
    "Export report": "Esporta report",
    "Close": "Chiudi",
    # -- options -------------------------------------------------------
    "Destination": "Destinazione",
    "Beside the original file": "Accanto al file originale",
    "One folder": "Cartella unica",
    "Mirror the source tree": "Ricrea la struttura delle cartelle",
    "Choose…": "Scegli…",
    "If the file exists": "Se il file esiste già",
    "Rename": "Rinomina",
    "Overwrite": "Sovrascrivi",
    "Skip": "Salta",
    "Include subfolders": "Includi sottocartelle",
    "Analyse only, do not extract": "Solo analisi, non estrarre",
    "Verify signatures": "Verifica le firme",
    "Parallel workers": "Elaborazioni in parallelo",
    "Options": "Opzioni",
    # -- queue table ----------------------------------------------------
    "File": "File",
    "Size": "Dimensione",
    "Status": "Stato",
    "Signatures": "Firme",
    "Signer": "Firmatario",
    "Content": "Contenuto",
    "Output": "Risultato",
    "Details": "Dettagli",
    "Queued": "In coda",
    "Working": "In corso",
    "Done": "Completato",
    "Warning": "Attenzione",
    "Skipped": "Saltato",
    "Failed": "Errore",
    "Cancelled": "Annullato",
    # -- details panel ---------------------------------------------------
    "Select a file to see its details": "Seleziona un file per vederne i dettagli",
    "Container": "Contenitore",
    "Encoding": "Codifica",
    "Signed content": "Contenuto firmato",
    "Nesting": "Annidamento",
    "Certificates": "Certificati",
    "Signature": "Firma",
    "Signatures found": "Firme trovate",
    "Signed on": "Firmato il",
    "Digest algorithm": "Algoritmo di digest",
    "Signature algorithm": "Algoritmo di firma",
    "Integrity": "Integrità",
    "Content matches the signed digest": "Il contenuto corrisponde al digest firmato",
    "Content does not match the signed digest":
        "Il contenuto NON corrisponde al digest firmato",
    "Not checked": "Non verificata",
    "Signature check": "Controllo della firma",
    "Signature matches the certificate's key":
        "La firma corrisponde alla chiave del certificato",
    "Signature does not match the certificate's key":
        "La firma NON corrisponde alla chiave del certificato",
    "Certificate": "Certificato",
    "Subject": "Soggetto",
    "Issuer": "Emittente",
    "Serial number": "Numero di serie",
    "Valid from": "Valido dal",
    "Valid until": "Valido fino al",
    "Valid at the time of signing": "Valido al momento della firma",
    "Not valid at the time of signing": "NON valido al momento della firma",
    "Expired": "Scaduto",
    "Currently valid": "Attualmente valido",
    "Key": "Chiave",
    "Fingerprint (SHA-256)": "Impronta (SHA-256)",
    "Qualified certificate": "Certificato qualificato",
    "Timestamp": "Marca temporale",
    "Timestamps": "Marche temporali",
    "Authority": "Autorità",
    "Counter-signatures": "Controfirme",
    "Commitment": "Impegno dichiarato",
    "Place": "Luogo",
    "Warnings": "Avvertenze",
    "Payload": "Documento estratto",
    "Type": "Tipo",
    "Written to": "Scritto in",
    "Not extracted": "Non estratto",
    # -- status bar and messages ------------------------------------------
    "Ready": "Pronto",
    "No file in the queue": "Nessun file in coda",
    "{n} files in the queue": "{n} file in coda",
    "Processing {done} of {total}": "Elaborazione {done} di {total}",
    "Finished: {ok} extracted, {warn} with warnings, {failed} failed":
        "Terminato: {ok} estratti, {warn} con avvertenze, {failed} con errori",
    "Finished: {ok} analysed, {warn} with warnings, {failed} failed":
        "Terminato: {ok} analizzati, {warn} con avvertenze, {failed} con errori",
    "Run cancelled": "Esecuzione annullata",
    "Nothing to do": "Niente da fare",
    "Add .p7m files or a folder to begin": "Aggiungi file .p7m o una cartella per iniziare",
    "Scanning folder…": "Scansione della cartella…",
    "No .p7m file found in {folder}": "Nessun file .p7m trovato in {folder}",
    "{n} files added": "{n} file aggiunti",
    "Choose the destination folder": "Scegli la cartella di destinazione",
    "Choose a folder to scan": "Scegli la cartella da analizzare",
    "Signed containers": "Buste firmate",
    "All files": "Tutti i file",
    "Report saved to {path}": "Report salvato in {path}",
    "Could not save the report: {error}": "Impossibile salvare il report: {error}",
    "CSV report": "Report CSV",
    "JSON report": "Report JSON",
    "Nothing to export yet": "Non c'è ancora niente da esportare",
    "A run is in progress. Cancel it and quit?":
        "Un'elaborazione è in corso. Annullarla e uscire?",
    "Quit": "Esci",
    "Stay": "Resta",
    # -- about ------------------------------------------------------------
    "About P7M Manager": "Informazioni su P7M Manager",
    "Inspect signed .p7m containers and extract what they carry":
        "Analizza le buste firmate .p7m ed estrae il documento contenuto",
    "Version {version}": "Versione {version}",
    "This tool checks integrity and, for RSA, the signature itself. It is not a "
    "legal validation: it has no trust list, does not check revocation and does "
    "not validate timestamps against an authority.":
        "Questo strumento verifica l'integrità e, per RSA, la firma stessa. Non è "
        "una validazione legale: non dispone di una lista di certificati fidati, "
        "non controlla la revoca e non convalida le marche temporali presso "
        "un'autorità.",
    "Free software under AGPL-3.0-or-later; a commercial licence is available.":
        "Software libero con licenza AGPL-3.0-or-later; è disponibile una licenza "
        "commerciale.",
}
