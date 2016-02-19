import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
	
	__tablename__ = 'user'
	
	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)
	email = Column(String(80))

	@property
	def serialize(self):
		return {
			'name': self.name,
			'id': self.id,
			'email': self.email,
		}

class Movie(Base):
	
	__tablename__= 'menu_item'

	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)
	datewatched = Column(Date)
	description = Column(String(250))
	review = Column(String(250))
	rating = Column(Integer)
	mdbid = Column(Integer)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		return {
			'name': self.name,
			'datewatched': self.datewatched,
			'id': self.id,
			'description': self.description,
			'review': self.review,
		}



engine = create_engine('sqlite:///movieratings.db')
Base.metadata.create_all(engine)
