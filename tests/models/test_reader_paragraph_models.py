from wenyan_models.reader.paragraph import ParagraphPackage, ReaderNote, ReaderSegment, ReaderToken


def test_paragraph_package_roundtrip_minimal():
    payload = {
        "id": "c777d984-afd6-4a31-aa34-2d26d29fb445",
        "segments": [
            {
                "id": "d70e05cc-a271-43e6-9abd-40c97c83bb96",
                "text": "孟子見梁惠王。",
                "newGlossIds": ["7d0d9c78-8307-4f11-9352-63b5d74af0fd"],
                "tokens": [
                    {
                        "id": "3723a8d9-6621-40e7-b444-2fcb3dcbcdcb",
                        "surface": "孟子",
                        "start": 0,
                        "end": 2,
                        "glossId": "7d0d9c78-8307-4f11-9352-63b5d74af0fd",
                    }
                ],
                "notes": [],
            }
        ],
    }
    model = ParagraphPackage.model_validate(payload)
    assert model.segments[0].tokens[0].gloss_id == "7d0d9c78-8307-4f11-9352-63b5d74af0fd"
    roundtrip = ParagraphPackage.model_validate(model.model_dump(by_alias=True))
    assert roundtrip == model
