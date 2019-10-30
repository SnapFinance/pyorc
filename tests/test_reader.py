import pytest

import io
import string

from pyorc import Reader, Writer, typedescription, TypeKind


@pytest.fixture
def orc_data():
    def _init(row):
        data = io.BytesIO()
        with Writer(data, "struct<col0:int,col1:string>") as writer:
            for i in range(row):
                writer.write(
                    {
                        "col0": i,
                        "col1": "Test {0}".format(string.ascii_uppercase[i % 26]),
                    }
                )
        data.seek(0)
        return data

    return _init


def test_next():
    data = io.BytesIO()
    Writer(data, "struct<col0:int,col1:string>").close()
    with pytest.raises(StopIteration):
        reader = Reader(data)
        next(reader)
    expected = {"col0": 0, "col1": "Test A"}
    data = io.BytesIO()
    with Writer(data, "struct<col0:int,col1:string>") as writer:
        writer.write(expected)
    reader = Reader(data)
    assert next(reader) == expected
    with pytest.raises(StopIteration):
        next(reader)


def test_iter(orc_data):
    reader = Reader(orc_data(20))
    result = [row for row in reader]
    assert len(result) == 20
    assert {"col0": 0, "col1": "Test A"} == result[0]
    assert {"col0": 19, "col1": "Test T"} == result[-1]
    assert {"col0": 12, "col1": "Test M"} in result


def test_len():
    data = io.BytesIO()
    Writer(data, "struct<col0:int,col1:string>").close()
    reader = Reader(data)
    assert len(reader) == 0

    data = io.BytesIO()
    with Writer(data, "struct<col0:int,col1:string>") as writer:
        writer.write({"col0": 0, "col1": "Test A"})
    reader = Reader(data)
    assert len(reader) == 1

    data = io.BytesIO()
    with Writer(data, "struct<col0:int,col1:string>") as writer:
        for i in range(10):
            writer.write({"col0": i, "col1": "Test"})
    reader = Reader(data)
    assert len(reader) == 10


def test_schema():
    schema_str = "struct<col0:int,col1:string>"
    data = io.BytesIO()
    Writer(data, schema_str).close()
    reader = Reader(data)

    assert str(reader.schema) == schema_str
    with pytest.raises(AttributeError):
        reader.schema = "fail"
    with pytest.raises(AttributeError):
        del reader.schema

    schema = reader.schema
    del reader
    assert isinstance(schema, typedescription)
    assert schema.kind == TypeKind.STRUCT


def test_current_row(orc_data):
    reader = Reader(orc_data(20))
    assert reader.current_row == 0
    for _ in range(10):
        _ = next(reader)
    assert reader.current_row == 10
    res = next(reader)
    assert reader.current_row == 11
    assert res["col0"] == 10
    _ = [_ for _ in reader]
    assert reader.current_row == len(reader)

    with pytest.raises(AttributeError):
        reader.current_row = "fail"
    with pytest.raises(AttributeError):
        del reader.current_row


def test_seek(orc_data):
    reader = Reader(orc_data(50))
    assert reader.seek(0) == 0
    assert reader.current_row == 0
    assert reader.seek(10) == 10
    assert reader.current_row == 10
    assert next(reader)["col0"] == 10
    assert reader.seek(0, 2) == len(reader)
    with pytest.raises(StopIteration):
        _ = next(reader)["col0"]
    assert reader.seek(-1, 2) == 49
    assert next(reader)["col0"] == 49
    assert reader.seek(-10, 2) == 40
    assert reader.seek(1, 1) == 41
    assert next(reader)["col0"] == 41
    reader.seek(10)
    assert reader.seek(8, 1) == 18
    assert reader.seek(-5, 1) == 13
    assert next(reader)["col0"] == 13
    with pytest.raises(ValueError):
        reader.seek(-1, 0)
    with pytest.raises(ValueError):
        reader.seek(10, 10)


def test_read(orc_data):
    reader = Reader(orc_data(80))
    result = reader.read()
    assert len(result) == len(reader)
    assert {"col0": 0, "col1": "Test A"} == result[0]
    assert {"col0": 25, "col1": "Test Z"} == result[25]
    assert result[-1]["col0"] == 79
    assert reader.current_row == 80
    with pytest.raises(StopIteration):
        _ = next(reader)
    result = reader.read()
    assert result == []

    reader = Reader(orc_data(80))
    with pytest.raises(ValueError):
        _ = reader.read(-5)
    with pytest.raises(TypeError):
        _ = reader.read("a")
    result = reader.read(10)
    assert len(result) == 10
    assert {"col0": 0, "col1": "Test A"} == result[0]
    assert {"col0": 9, "col1": "Test J"} == result[-1]

    result = reader.read(15)
    assert len(result) == 15
    assert {"col0": 10, "col1": "Test K"} == result[0]
    assert {"col0": 24, "col1": "Test Y"} == result[-1]
    assert reader.current_row == 25

    result = reader.read()
    assert len(result) == 55
    assert {"col0": 25, "col1": "Test Z"} == result[0]

    reader = Reader(orc_data(80))
    result = reader.read(0)
    assert result == []
    result = reader.read(-1)
    assert len(result) == len(reader)
