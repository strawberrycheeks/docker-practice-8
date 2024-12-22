import glossary_pb2
import glossary_pb2_grpc
import grpc
from concurrent import futures
from sqlalchemy import Column, Integer, String, create_engine 
from sqlalchemy.orm import sessionmaker, declarative_base


INITIAL_TERMS = [
    {"word": "Архитектура программной системы", "meaning": "Структурное представление программной системы, включающее описание компонентов, их взаимодействий, поведения и ограничений."},
    {"word": "Контейнеризация", "meaning": "Технология упаковки программного обеспечения и всех его зависимостей в изолированный контейнер для обеспечения согласованности среды выполнения на разных платформах."},
    {"word": "Непрерывное развертывание", "meaning": "Подход в разработке программного обеспечения, при котором изменения в коде автоматически проходят все этапы подготовки и развертываются на рабочем сервере без ручного вмешательства."},
]


SQLITE_DATABASE_FILE = 'glossary.db'
SQLITE_DATABASE_URL  = f'sqlite:///{SQLITE_DATABASE_FILE}'

connect_args = {"check_same_thread": False}
engine = create_engine(SQLITE_DATABASE_URL, connect_args=connect_args, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TermModel(Base):
    __tablename__ = "terms"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    word = Column(String, unique=True, index=True)
    meaning = Column(String)


class Glossary(glossary_pb2_grpc.GlossaryServicer):
    def GetAllTerms(self, request, context):
        db = SessionLocal()
        terms = db.query(TermModel).all()
        db.close()

        terms = [glossary_pb2.Term(id=term.id, word=term.word, meaning=term.meaning) for term in terms]
        return glossary_pb2.TermsList(terms=terms)


    def GetTerm(self, request, context):
        db = SessionLocal()
        db_term = db.query(TermModel).filter(TermModel.id == request.id).first()
        db.close()

        if db_term:
            term = glossary_pb2.Term(id=db_term.id, word=db_term.word, meaning=db_term.meaning)
            return glossary_pb2.GetTermResponse(term=term)
        
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Term not found")
        return glossary_pb2.GetTermResponse()


    def CreateTerm(self, request, context):
        db = SessionLocal()
        db_term = TermModel(
            word=request.word,
            meaning=request.meaning,
        )
        db.add(db_term)
        db.commit()
        db.close()

        return glossary_pb2.CreateTermResponse(message="Term added successfully!")


    def DeleteTerm(self, request, context):
        db = SessionLocal()
        db_term = db.query(TermModel).filter(TermModel.id == request.id).first()
        if db_term:
            db.delete(db_term)
            db.commit()
            db.close()
            return glossary_pb2.DeleteTermResponse(message="Term deleted successfully!")
        
        db.close()
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Term not found")
        return glossary_pb2.DeleteTermResponse(message="Term not found")


    def UpdateTerm(self, request, context):
        db = SessionLocal()
        db_term = db.query(TermModel).filter(TermModel.id == request.term.id).first()
        if db_term:
            db_term.word = request.term.word
            db_term.meaning = request.term.meaning
            db.commit()
            db.close()
            return glossary_pb2.UpdateTermResponse(message="Term updated successfully!")
        
        db.close()
        context.set_code(grpc.StatusCode.NOT_FOUND)
        context.set_details("Term not found")
        return glossary_pb2.UpdateTermResponse(message="Term not found")


def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    for term in INITIAL_TERMS:
        if not db.query(TermModel).filter(TermModel.word == term['word']).first():
            db.add(TermModel(**term))
    db.commit()
    db.close()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    glossary_pb2_grpc.add_GlossaryServicer_to_server(Glossary(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    create_db_and_tables()
    serve()
    