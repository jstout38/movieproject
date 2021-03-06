#Does the initial set up of the database upon execution on command line, also contains functions that serialize data for jsonification

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
    picture = Column(String(250))
    movies = relationship("Movie", cascade="all, delete-orphan")

    #Return jsonified data for each object in a collection
    @property
    def serialize(self):
    	return {
			'name': self.name,
			'id': self.id,
			'email': self.email,
			'picture': self.picture
		}


class Movie(Base):
	
	__tablename__= 'menu_item'
	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)
	datewatched = Column(String(250))
	description = Column(String(2000))
	review = Column(String(2000))
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


engine = create_engine('postgres://afmaywensnnldv:p5LzOYcun5fEgr5aougoyg917H@ec2-54-83-3-38.compute-1.amazonaws.com:5432/d60gq6hm9tap55')
Base.metadata.create_all(engine)
