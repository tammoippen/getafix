"""§3.1 — line-level product groups (BG-32 / BG-33 / BG-34).

EN 16931 enriches every invoice line's :class:`TradeProduct` with
three optional sub-groups:

* **BG-32 ``ApplicableProductCharacteristic``** — name/value pairs
  describing the item (BT-160 / BT-161). Both required when the
  group is present (``BR-54``).
* **BG-33 ``DesignatedProductClassification``** — coded item
  classification with a scheme identifier (BT-158 / BT-158-1 /
  BT-158-2). Scheme identifier required when ``ClassCode`` is set
  (``BR-65``).
* **BG-34 ``OriginTradeCountry``** — single ISO 3166-1 alpha-2
  country code (BT-159) identifying where the item originated.

All three ship at COMFORT+. The tests below pin the construction
shape, the rendered XML order (XSD sequence: characteristics →
classifications → origin country), and the parse round-trip.
"""

from __future__ import annotations

import pytest as pt

from getafix.schema import Profile
from getafix.schema.element import ProfileMismatch
from getafix.schema.line import (
    OriginCountry,
    ProductCharacteristic,
    ProductClassification,
    TradeProduct,
)
from tests._fixtures import wrap_subtree
from tests._parsers import ParseFromBytes


class TestProductCharacteristic:
    def test_construct_with_description_and_value(self) -> None:
        c = ProductCharacteristic(description="colour", value="red")
        assert c.description == "colour"
        assert c.value == "red"

    def test_renders_at_comfort(self) -> None:
        c = ProductCharacteristic(description="colour", value="red")
        xml = c.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:Description>" in xml
        assert "colour" in xml
        assert "<ram:Value>" in xml
        assert "red" in xml

    def test_parent_render_below_comfort_raises(self) -> None:
        """The COMFORT class profile only fires when a parent renders
        the child — calling ``to_xml_internal`` directly skips the
        gate, but embedding the characteristic on a ``TradeProduct``
        and rendering the parent at BASIC must raise."""
        prod = TradeProduct(
            name="W",
            characteristics=[ProductCharacteristic(description="colour", value="red")],
        )
        with pt.raises(ProfileMismatch):
            prod.to_xml_internal(Profile.BASIC).render(indent=True)


class TestProductClassification:
    def test_construct_with_code_and_scheme(self) -> None:
        c = ProductClassification(class_code="12345", list_id="TST")
        assert c.class_code == "12345"
        assert c.list_id == "TST"

    def test_list_id_required(self) -> None:
        with pt.raises(TypeError):
            _ = ProductClassification(class_code="12345")  # type: ignore[call-arg]

    def test_renders_scheme_attribute(self) -> None:
        c = ProductClassification(class_code="12345", list_id="TST")
        xml = c.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert '<ram:ClassCode listID="TST">' in xml
        assert "12345" in xml

    def test_renders_list_version_id(self) -> None:
        c = ProductClassification(
            class_code="12345", list_id="TST", list_version_id="v2"
        )
        xml = c.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert 'listID="TST"' in xml
        assert 'listVersionID="v2"' in xml


class TestOriginCountry:
    def test_construct_with_country_code(self) -> None:
        c = OriginCountry(id="DE")
        assert c.id == "DE"

    def test_renders_country_id(self) -> None:
        c = OriginCountry(id="DE")
        xml = c.to_xml_internal(Profile.COMFORT).render(indent=True)
        assert "<ram:ID>" in xml
        assert "DE" in xml


class TestTradeProductIntegration:
    """The three groups slot into ``TradeProduct`` after the existing
    BT-153/154/155/156 fields. XSD sequence: characteristics →
    classifications → origin_country."""

    def test_product_carries_all_three_groups(self) -> None:
        prod = TradeProduct(
            name="W",
            characteristics=[
                ProductCharacteristic(description="colour", value="red"),
                ProductCharacteristic(description="weight", value="1kg"),
            ],
            classifications=[ProductClassification(class_code="12345", list_id="TST")],
            origin_country=OriginCountry(id="DE"),
        )
        xml = prod.to_xml_internal(Profile.COMFORT).render(indent=True)
        # Order: every characteristic before the classification before the country.
        i_char = xml.find("<ram:ApplicableProductCharacteristic>")
        i_class = xml.find("<ram:DesignatedProductClassification>")
        i_origin = xml.find("<ram:OriginTradeCountry>")
        assert 0 <= i_char < i_class < i_origin

    def test_round_trip(self, parser: ParseFromBytes) -> None:
        prod = TradeProduct(
            name="W",
            characteristics=[ProductCharacteristic(description="colour", value="red")],
            classifications=[
                ProductClassification(
                    class_code="12345", list_id="TST", list_version_id="v2"
                )
            ],
            origin_country=OriginCountry(id="DE"),
        )
        xml = prod.to_xml_internal(Profile.COMFORT).render(indent=True)
        parsed = TradeProduct.from_xml(
            parser(wrap_subtree(xml, "SpecifiedTradeProduct"))
        )
        assert parsed == prod

    def test_product_without_new_groups_still_works(self) -> None:
        prod = TradeProduct(name="W")
        xml = prod.to_xml_internal(Profile.BASIC).render(indent=True)
        assert "<ram:ApplicableProductCharacteristic>" not in xml
        assert "<ram:DesignatedProductClassification>" not in xml
        assert "<ram:OriginTradeCountry>" not in xml
