from fastapi import FastAPI, HTTPException
import glossary_pb2
import glossary_pb2_grpc
from google.protobuf.empty_pb2 import Empty
import grpc
from pydantic import BaseModel
from typing import List


class Term(BaseModel):
    id: int
    word: str
    meaning: str


class TermsList(BaseModel):
    terms: List[Term]


class CreateTermRequest(BaseModel):
    word: str
    meaning: str


class CreateTermResponse(BaseModel):
    message: str


class DeleteTermResponse(BaseModel):
    message: str


class GetTermRequest(BaseModel):
    id: int


class GetTermResponse(BaseModel):
    term: Term


class UpdateTermRequest(BaseModel):
    term: Term


class UpdateTermResponse(BaseModel):
    message: str


GRPC_SERVER_HOST = 'glossary-server'
GRPC_SERVER_PORT = 50051


channel = grpc.insecure_channel(f"{GRPC_SERVER_HOST}:{GRPC_SERVER_PORT}")
stub = glossary_pb2_grpc.GlossaryStub(channel)

app = FastAPI()


@app.get("/terms", response_model=TermsList)
async def read_terms():
    response = stub.GetAllTerms(Empty())
    # TODO: проверить, можно ли убрать отсюда приведение к типу
    terms = [Term(id=term.id, word=term.word, meaning=term.meaning) for term in response.terms]
    return TermsList(terms=terms)


@app.get("/terms/{term_id}", response_model=GetTermResponse)
async def read_term(term_id: int):
    response = stub.GetTerm(glossary_pb2.GetTermRequest(id=term_id))
    if response.term:
        return GetTermResponse(term=Term(id=response.term.id, word=response.term.word, meaning=response.term.meaning))
    raise HTTPException(status_code=404, detail="Term not found")


@app.post("/terms", response_model=CreateTermResponse)
async def create_term(request: CreateTermRequest):
    response = stub.CreateTerm(glossary_pb2.CreateTermRequest(word=request.word, meaning=request.meaning))
    return CreateTermResponse(message=response.message)


@app.put("/terms", response_model=UpdateTermResponse)
async def update_term(request_term: UpdateTermRequest):
    try:
        term = glossary_pb2.Term(
            id=request_term.term.id,
            word=request_term.term.word,
            meaning=request_term.term.meaning,
        )
        response = stub.UpdateTerm(glossary_pb2.UpdateTermRequest(term=term))
        return UpdateTermResponse(message=response.message)
    except grpc.RpcError as e:
        raise HTTPException(status_code=404 if e.code() == grpc.StatusCode.NOT_FOUND else 500, detail=e.details())


@app.delete("/terms/{term_id}", response_model=DeleteTermResponse)
async def delete_term(term_id: int):
    try:
        response = stub.DeleteTerm(glossary_pb2.DeleteTermRequest(id=term_id))
        return DeleteTermResponse(message=response.message)
    except grpc.RpcError as e:
        raise HTTPException(status_code=404 if e.code() == grpc.StatusCode.NOT_FOUND else 500, detail=e.details())

