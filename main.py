import uvicorn
# uvicorn main:app --reload
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head

from fastapi import FastAPI, status, Body, HTTPException, Request, Form
from fastapi.responses import HTMLResponse

from fastapi import APIRouter, Depends, status, HTTPException
from slugify import slugify
from sqlalchemy.orm import Session
from starlette.staticfiles import StaticFiles

from app.backend.db_depends import get_db

from typing import Annotated
from fastapi.templating import Jinja2Templates

from app.models.game import Game
from app.models.user import User
from app.models.user_game_feedback import UserGameFeedback
from app.models.user_game_rating import UserGameRating

from app.routers import user, game, user_game_feedback, user_game_rating

from sqlalchemy import insert, select, update, delete

app = FastAPI()
templates = Jinja2Templates(directory='templates')

app.mount("/photo", StaticFiles(directory="photo"), name="photo")


@app.get("/")
async def get_welcome(request: Request) -> HTMLResponse:
    '''
    :param request:
    :return: 'welcome.html', {"request": request}
    функция переводит пользователя на главный экран приложения
    '''
    return templates.TemplateResponse('welcome.html', {"request": request})


@app.get("/list_user")
async def get_list_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :return: 'list_user.html', {"request": request, "users": users}
    Функция возвращает список зарегистрированных пользователей
    '''
    users = db.scalars(select(User)).all()
    return templates.TemplateResponse('list_user.html', {"request": request, "users": users})


@app.get("/list_game")
async def get_list_game(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :return: 'list_games.html', {"request": request, "games": games}
    Функция возвращает список игр
    '''
    games = db.scalars(select(Game)).all()
    return templates.TemplateResponse('list_games.html', {"request": request, "games": games})


@app.get("/list_game/{game_id}")
async def get_game(request: Request, db: Annotated[Session, Depends(get_db)], game_id: int) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :param game_id: int
    :return: 'game.html', {"request": request, "game": game, "ratings": ratings, "feedbacks": feedbacks}
    Функция возвращает информацию о конкретной игре
    '''
    game = db.scalar(select(Game).where(Game.id == game_id))

    ratings_query = select(UserGameRating, User).join(User).where(UserGameRating.game_id == game_id)
    ratings = db.execute(ratings_query).all()

    feedbacks_query = select(UserGameFeedback, User).join(User).where(UserGameFeedback.game_id == game_id)
    feedbacks = db.execute(feedbacks_query).all()

    return templates.TemplateResponse('game.html', {"request": request,
                                                    "game": game,
                                                    "ratings": ratings,
                                                    "feedbacks": feedbacks})


@app.get("/list_user/{user_id}")
async def get_user(request: Request, db: Annotated[Session, Depends(get_db)], user_id: int) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :param user_id: int
    :return: 'user.html', { "request": request, "user": user, "ratings": ratings, "feedbacks": feedbacks}
    Функция возвращает информацию о конкретном пользователе
    '''
    user = db.scalar(select(User).where(User.id == user_id))

    ratings_query = select(UserGameRating, Game).join(Game).where(UserGameRating.user_id == user_id)
    ratings = db.execute(ratings_query).all()

    feedbacks_query = (select(UserGameFeedback, Game).join(Game).where(UserGameFeedback.user_id == user_id))
    feedbacks = db.execute(feedbacks_query).all()

    return templates.TemplateResponse('user.html', {
        "request": request,
        "user": user,
        "ratings": ratings,
        "feedbacks": feedbacks
    })


@app.get("/regist_user")
async def get_registration_form(request: Request):
    '''
    :param request: Request
    :return: regist_user.html", {"request": request}
    Функция возвращает форму для регистрации пользователя
    '''
    return templates.TemplateResponse("regist_user.html", {"request": request})


@app.post("/register")
async def reg_user(request: Request, db: Annotated[Session, Depends(get_db)], username: str = Form(...),
                   firstname: str = Form(...), lastname: str = Form(...), password: str = Form(...)) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :param username: str = Form(...)
    :param firstname: str = Form(...)
    :param lastname: Form(...)
    :param password: Form(...))
    :return: 'welcome_user.html', {"request": request, "username": username, 'user_id': user_id}
    Функция обрабатывает информацию, полученную при регистрации пользователя, и добавляет её в базу данных.
    Если логин уже есть в базе данных, то выводится ошибка и сообщение "Логин уже занят((( Попробуйте другой"
    '''
    user = db.scalar(select(User).where(User.username == username))
    if user:
        return HTMLResponse(f'Логин уже занят((( Попробуйте другой', status_code=400)
    db.execute(insert(User).values(username=username,
                                   firstname=firstname,
                                   lastname=lastname,
                                   password=password,
                                   slug=slugify(username)))
    db.commit()
    user_id = db.scalar(select(User.id).where(User.username == username))
    return templates.TemplateResponse('welcome_user.html', {"request": request, "username": username,
                                                            'user_id': user_id})


# __________________________________________добавить отзыв_______________________________________________________________
@app.get("/feedback_entry")
async def feedback_entry(request: Request):
    '''
    :param request: Request
    :return: feedback_entry.html", {"request": request}
    Функция возвращает форму для проверки налиция регистрации у пользователя
    '''
    return templates.TemplateResponse("feedback_entry.html", {"request": request})


@app.post("/check_feedback_entry")
async def feedback_entry(request: Request, db: Annotated[Session, Depends(get_db)], username: str = Form(...),
                         password: str = Form(...), user_id: int = Form(...)) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :param username: str = Form(...),
    :param password: str = Form(...)
    :param user_id: int = Form(...)
    :return: feedback_entry.html', {"request": request, 'error': error}
    Функция обрабатывает информацию, полученную при проверки пользователя на наличие регистрации.
    Если id пользователя нет в базе данных, то выводится надпись:"Пользователь не найден -_-\nПопробуйте снова"
    Если введенные данные не совпадаю с теми, что записаны в базе данных, то выводится ошибка с надписью:
    "Что-то пошло не так ((\nПопробуйте снова"
    '''
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        error = 'Пользователь не найден -_-\nПопробуйте снова'
        return templates.TemplateResponse('feedback_entry.html', {"request": request, 'error': error})

    if username == user.username and password == user.password and user_id == user.id:
        global global_user
        global_user = user
        return templates.TemplateResponse('feedback.html', {"request": request})
    else:
        error = 'Что-то пошло не так ((\nПопробуйте снова'
        return templates.TemplateResponse('feedback_entry.html', {"request": request, 'error': error})


@app.get("/feedback")
async def feedback(request: Request):
    '''
    :param request: Request
    :return: "feedback.html", {"request": request}
    Функция возвращает форму для оставления отзыва к игре.
    '''
    return templates.TemplateResponse("feedback.html", {"request": request})


@app.post("/feedback_finish")
async def feedback(request: Request, db: Annotated[Session, Depends(get_db)], feedback_text: str = Form(...),
                   game_id: int = Form(...)) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :param feedback_text: str = Form(...)
    :param game_id: int = Form(...)
    :return: 'finish_feedback.html', {"request": request}
    Функция обрабатывает информацию, полученную от пользователя при оставлении отзыва.
    Если отзыв у пользователя к игре уже есть, то отзыв будет отредактирован.
    Если id игры нет в базе данные, выводится ошибка с надписью "GAME NOT FOUND".
    '''
    if global_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not authenticated")
    user_id = global_user.id

    game = db.scalar(select(Game).where(Game.id == game_id))
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GAME NOT FOUND")

    existing_feedback = db.scalar(select(UserGameFeedback).where(
        UserGameFeedback.user_id == user_id, UserGameFeedback.game_id == game_id))
    if existing_feedback is not None:
        existing_feedback.feedback_text = feedback_text
        db.commit()
    else:
        db.execute(insert(UserGameFeedback).values(user_id=global_user.id,
                                                   game_id=game_id,
                                                   feedback_text=feedback_text))
        db.commit()
    return templates.TemplateResponse('finish_feedback.html',
                                      {"request": request})


# __________________________________________добавить оценку______________________________________________________________
@app.get("/rating_entry")
async def rating_entry(request: Request):
    '''
    :param request: Request
    :return: "rating_entry.html", {"request": request}
    Функция возвращает форму для проверки налиция регистрации у пользователя
    '''
    return templates.TemplateResponse("rating_entry.html", {"request": request})


@app.post("/check_rating_entry")
async def check_rating_entry(request: Request, db: Annotated[Session, Depends(get_db)], username: str = Form(...),
                             password: str = Form(...), user_id: int = Form(...)) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :param username: str = Form(...),
    :param password: str = Form(...)
    :param user_id: int = Form(...)
    :return: 'rating_entry.html', {"request": request, 'error': error}
    Функция обрабатывает информацию, полученную при проверки пользователя на наличие регистрации.
    Если id пользователя нет в базе данных, то выводится надпись:"Пользователь не найден -_-\nПопробуйте снова"
    Если введенные данные не совпадаю с теми, что записаны в базе данных, то выводится ошибка с надписью:
    "Что-то пошло не так ((\nПопробуйте снова"
    '''
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        error = 'Пользователь не найден -_-\nПопробуйте снова'
        return templates.TemplateResponse('rating_entry.html', {"request": request, 'error': error})

    if username == user.username and password == user.password and user_id == user.id:
        global global_user
        global_user = user
        return templates.TemplateResponse('rating.html', {"request": request})
    else:
        error = 'Что-то пошло не так ((\nПопробуйте снова'
        return templates.TemplateResponse('rating_entry.html', {"request": request, 'error': error})


@app.get("/rating")
async def rating(request: Request):
    '''
    :param request: Request
    :return: "rating.html", {"request": request}
    Функция возвращает форму для оставления оценки.
    '''
    return templates.TemplateResponse("rating.html", {"request": request})


@app.post("/rating_finish")
async def rating_finish(request: Request, db: Annotated[Session, Depends(get_db)], rating_int: int = Form(...),
                        game_id: int = Form(...)) -> HTMLResponse:
    '''
    :param request: Request
    :param db: Annotated[Session, Depends(get_db)]
    :rating_int: int = Form(...)
    :param game_id: int = Form(...)
    :return: 'finish_feedback.html', {"request": request}
    Функция обрабатывает информацию, полученную от пользователя при оставлении оценки.
    Если оценка у пользователя к игре уже есть, то оценка будет отредактирован.
    Если id игры нет в базе данные, выводится ошибка с надписью "GAME NOT FOUND".
    Если оценка выйдет из диапазона 0-10, то выведится ошибка.
    '''
    if global_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not authenticated")
    user_id = global_user.id

    game = db.scalar(select(Game).where(Game.id == game_id))
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GAME NOT FOUND")

    if rating_int > 10:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Моre 10")
    if rating_int < 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Less 10")
    existing_rating = db.scalar(select(UserGameRating).where(
        UserGameRating.user_id == user_id, UserGameRating.game_id == game_id))
    if existing_rating is not None:
        existing_rating.rating_int = rating_int
        db.commit()
    else:
        db.execute(insert(UserGameRating).values(user_id=global_user.id,
                                                 game_id=game_id,
                                                 rating_int=rating_int))
        db.commit()
    return templates.TemplateResponse('finish_feedback.html',
                                      {"request": request})


app.include_router(user.router_user)
app.include_router(game.router_game)
app.include_router(user_game_feedback.router_feedback)
app.include_router(user_game_rating.router_rating)
