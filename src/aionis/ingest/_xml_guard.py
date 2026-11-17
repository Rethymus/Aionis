"""XXE / entity-expansion guard for untrusted XML — hand-rolled ``forbid_dtd``.

Why (premise pinned live on this machine 2026-11-17, re-pinned by
``tests/test_xml_guard.py``): expat **2.6.2** — below the 2.7.2 entity
hardening cited by the OWASP XML prevention guidance — and stock
``ET.fromstring`` expands nested internal entities without complaint: a
5-layer x10 "mini billion laughs" expands to 100,000 characters with no
error. External entities are refused by expat's defaults ("undefined
entity"), but that is no defense against the internal-entity expansion
blowup, and Python's stdlib xml docs put entity-expansion protection on the
CALLER. This module is that caller-side guard: any ``<!DOCTYPE`` declaration
— the only syntactic place an ``<!ENTITY`` may appear — is refused before
the DTD is read. Semantics equal ``defusedxml``'s ``forbid_dtd``, hand-rolled
with zero new dependencies.

Technique (mirrors ``defusedxml._get_py3_cls``, which lifts
``test.support.import_fresh_module``): the C-accelerated
``_elementtree.XMLParser`` exposes no underlying expat object, so the
PURE-PYTHON ``XMLParser`` class is imported once with the accelerator masked
out of ``sys.modules``; its instances carry ``.parser`` (a
``pyexpat.xmlparser``) whose ``StartDoctypeDeclHandler`` raises, aborting the
parse the moment a DOCTYPE appears. The pure module's ``ParseError`` is
rebound to the C ``ET.ParseError`` so callers catching ``ET.ParseError`` see
identical behavior for non-DTD malformations.

Honest scope: this refuses DTDs (hence every ENTITY declaration, internal or
external). It does not attempt DTD-but-no-entities parsing — a refused
document is refused whole, fail-closed.
"""
from __future__ import annotations

import importlib
import sys
import xml.etree.ElementTree as ET


class XmlDtdForbiddenError(ValueError):
    """XML refused: DOCTYPE/DTD declarations are forbidden (XXE guard)."""


def _pure_xmlparser_cls() -> type:
    """Import the pure-Python ``ET.XMLParser`` class, accelerator masked.

    Must run AFTER ``xml.etree.ElementTree`` is already imported (this
    module's top-level import guarantees that), so the restore in ``finally``
    always puts the C-backed module back. Everything except the two popped
    entries is untouched; the dance runs once per process, at import time.
    """
    pymodname = "xml.etree.ElementTree"
    cmodname = "_elementtree"
    pymod = sys.modules.pop(pymodname, None)
    cmod = sys.modules.pop(cmodname, None)
    sys.modules[cmodname] = None  # accelerator "not found" -> pure fallback
    try:
        pure_pymod = importlib.import_module(pymodname)
    finally:
        sys.modules[pymodname] = pymod
        if cmod is not None:
            sys.modules[cmodname] = cmod
        # keep the xml.etree package attribute pointing at the C-backed module
        etree_pkg = sys.modules.get("xml.etree")
        if pymod is not None and etree_pkg is not None:
            etree_pkg.ElementTree = pymod
    # Callers catch the C ET.ParseError; make the pure parser raise that one.
    pure_pymod.ParseError = ET.ParseError
    return pure_pymod.XMLParser


_PURE_XMLPARSER = _pure_xmlparser_cls()


def fromstring_no_dtd(data: bytes | str) -> ET.Element:
    """``ET.fromstring`` with DOCTYPE/ENTITY declarations refused.

    Raises :class:`XmlDtdForbiddenError` the moment a ``<!DOCTYPE`` is seen;
    every non-DTD condition (malformed XML, undefined entity, ...) behaves
    exactly like stock ``ET.fromstring`` — same ``ET.ParseError`` the callers
    already catch.
    """
    parser = _PURE_XMLPARSER()

    def _forbid_dtd(*args: object, **kwargs: object) -> None:
        raise XmlDtdForbiddenError(
            "DOCTYPE declaration forbidden — untrusted XML (XXE/entity-expansion guard)"
        )

    parser.parser.StartDoctypeDeclHandler = _forbid_dtd
    return ET.fromstring(data, parser=parser)


__all__ = ["XmlDtdForbiddenError", "fromstring_no_dtd"]
