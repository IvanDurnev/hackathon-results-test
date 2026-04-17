import aiohttp
import asyncio
import os
import requests
from urllib.parse import urlencode


class Bot:
    def __init__(self, token):
        self.token = token
        self.url = f'https://api.telegram.org/bot{token}/'

    async def __send_request(self, method, params=None):
        task = ''
        async with aiohttp.ClientSession() as session:
            task = asyncio.create_task(session.get(self.url + method + urlencode(params)))
            await asyncio.gather(task)

    async def get_me(self):
        method = 'getMe'
        await self.__send_request(method)

    async def send_message(self, chat_id, text, parse_mode='', disable_web_page_preview=False,
                           disable_notification=False, reply_to_message_id='', reply_markup=''):
        method = 'sendMessage?'
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': disable_web_page_preview,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': reply_markup
        }
        response = await self.__send_request(method, params)

    # def send_message_sync(self, chat_id, text, parse_mode='', disable_web_page_preview=False,
    #                  disable_notification=False, reply_to_message_id='', reply_markup=''):
    #     method = 'sendMessage?'
    #     params = {
    #         'chat_id': chat_id,
    #         'text': text,
    #         'parse_mode': parse_mode,
    #         'disable_web_page_preview': disable_web_page_preview,
    #         'disable_notification': disable_notification,
    #         'reply_to_message_id': reply_to_message_id,
    #         'reply_markup': reply_markup
    #     }
    #     requests.post(url=self.url + method, params=params)

    async def send_messages_list(self, users, text, parse_mode, reply_markup=''):
        tasks = []
        async with aiohttp.ClientSession() as session:
            for user in users:
                task = asyncio.create_task(self.send_message(chat_id=user.tg_id,
                                                             text=text,
                                                             parse_mode=parse_mode,
                                                             reply_markup=reply_markup))
                tasks.append(task)
            await asyncio.gather(*tasks)

    async def edit_message(self, chat_id, text, message_id, reply_markup='', parse_mode=''):
        method = 'editMessageText?'
        params = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'reply_markup': reply_markup,
            'parse_mode': parse_mode
        }
        await self.__send_request(method, params)

    async def forward_message(self, chat_id, from_chat_id, message_id, disable_notification=True):
        method = 'forwardMessage?'
        params = {
            'chat_id': chat_id,
            'from_chat_id': from_chat_id,
            'disable_notification': disable_notification,
            'message_id': message_id
        }
        response = await self.__send_request(method, params)

    async def edit_message_caption(self, chat_id, message_id, caption, inline_message_id='', reply_markup='', parse_mode=''):
        method = 'editMessageCaption?'
        params = {
            'chat_id': chat_id,
            'message_id': message_id,
            'inline_message_id': inline_message_id,
            'caption': caption,
            'reply_markup': reply_markup,
            'parse_mode': parse_mode
        }
        await self.__send_request(method, params)

    async def delete_message(self, chat_id='', message_id=''):
        method = 'deleteMessage?'
        params = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        await self.__send_request(method, params)

    async def send_photo(self, chat_id, photo, caption, parse_mode='', disable_notification=False, reply_to_message_id='',
                   reply_markup=''):
        method = 'sendPhoto?'
        try:
            with open(photo, 'rb') as document:
                filename = os.path.basename(photo)
                params = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification,
                    'reply_to_message_id': reply_to_message_id,
                    'reply_markup': reply_markup
                }
                files = {
                    'photo': (filename, document, 'multipart/form-data')
                }
                if type(chat_id) == list:
                    print(chat_id)
                    tasks = []
                    async with aiohttp.ClientSession() as session:
                        for user in chat_id:
                            task = asyncio.create_task(self.send_photo(chat_id=user.tg_id, photo=photo, caption=caption,
                                                                       parse_mode=parse_mode, reply_markup=reply_markup))
                            tasks.append(task)
                        await asyncio.gather(*tasks)
                else:
                    response = requests.post(url=self.url + method, params=params, files=files)
                    return response
        except FileNotFoundError:
            params = {
                'chat_id': chat_id,
                'photo': photo,
                'caption': caption,
                'parse_mode': parse_mode,
                'disable_notification': disable_notification,
                'reply_to_message_id': reply_to_message_id,
                'reply_markup': reply_markup
            }
            if type(chat_id) == list:
                tasks = []
                async with aiohttp.ClientSession() as session:
                    for user in chat_id:
                        task = asyncio.create_task(self.send_photo(chat_id=user.tg_id, photo=photo, caption=caption,
                                                                   parse_mode=parse_mode, reply_markup=reply_markup))
                        tasks.append(task)
                    await asyncio.gather(*tasks)
            else:
                await self.__send_request(method, params)

    async def send_animation(self, chat_id, animation, caption):
        method = 'sendAnimation?'
        params = {
            'chat_id': chat_id,
            'animation': animation,
            'caption': caption,
        }
        await self.__send_request(method, params)

    async def send_video(self, chat_id, video, caption='', width='', height='', parse_mode='',
                         disable_notification=False, reply_to_message_id='', reply_markup='' ):
        method = 'sendVideo?'
        try:
            with open(video, 'rb') as document:
                filename = os.path.basename(video)
                params = {
                    'chat_id': chat_id,
                    'caption': caption,
                    'parse_mode': parse_mode,
                    'disable_notification': disable_notification,
                    'reply_to_message_id': reply_to_message_id,
                    'reply_markup': reply_markup,
                    'width': width,
                    'height': height,
                }
                files = {
                    'video': (filename, document, 'multipart/form-data')
                }
                if type(chat_id) == list:
                    tasks = []
                    async with aiohttp.ClientSession() as session:
                        for user in chat_id:
                            task = asyncio.create_task(self.send_video(chat_id=user.tg_id, video=video, caption=caption,
                                                                       parse_mode=parse_mode, reply_markup=reply_markup))
                            tasks.append(task)
                        await asyncio.gather(*tasks)
                else:
                    response = requests.post(url=self.url + method, params=params, files=files)
                    return response
        except FileNotFoundError:
            params = {
                'chat_id': chat_id,
                'video': video,
                'caption': caption,
                'parse_mode': parse_mode,
                'disable_notification': disable_notification,
                'reply_to_message_id': reply_to_message_id,
                'reply_markup': reply_markup
            }
            if type(chat_id) == list:
                tasks = []
                async with aiohttp.ClientSession() as session:
                    for user in chat_id:
                        task = asyncio.create_task(self.send_video(chat_id=user.tg_id, video=video, caption=caption,
                                                                   parse_mode=parse_mode, reply_markup=reply_markup))
                        tasks.append(task)
                    await asyncio.gather(*tasks)
            else:
                await self.__send_request(method, params)

    async def send_chat_action(self, chat_id, action='upload_video'):
        method = 'sendChatAction?'
        params = {
            'chat_id': chat_id,
            'action': action
        }
        await self.__send_request(method, params)

    def send_document(self, chat_id, document_path, reply_to_message_id=''):
        method = 'sendDocument?'
        document = open(document_path, 'rb')
        filename = os.path.basename(document_path)
        params = {
            'chat_id': chat_id,
            'reply_to_message_id': reply_to_message_id
        }
        files = {
            'document': (filename, document, 'multipart/form-data')
        }
        requests.post(url=self.url + method, params=params, files=files)

    async def send_dice(self, chat_id, emoji='', disable_notification=False, reply_to_message_id='', reply_markup=''):
        method = 'sendDice?'
        params = {
            'chat_id': chat_id,
            'emoji': emoji,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': reply_markup,
        }
        await self.__send_request(method, params)

    async def send_poll(self, chat_id, question, options, type, allows_multiple_answers=False, correct_option_id='',
                        explanation='', explanation_parse_mode='Markdown', is_anonymous=False, open_period='',
                        close_date='', is_closed=False, disable_notification=False, reply_to_message_id='',
                        reply_markup=''):
        method = 'sendPoll?'
        params = {
            'chat_id': chat_id,
            'question': question,
            'options': options,
            'type': type,
            'allows_multiple_answers': allows_multiple_answers,
            'correct_option_id': correct_option_id,
            'explanation': explanation,
            'explanation_parse_mode': explanation_parse_mode,
            'is_anonymous': is_anonymous,
            'open_period': open_period,
            'close_date': close_date,
            'is_closed': is_closed,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': reply_markup,
        }
        await self.__send_request(method, params)

    async def send_poll_to_list(self, users, question, options, type, allows_multiple_answers=False, correct_option_id='',
                                explanation='', explanation_parse_mode='Markdown', is_anonymous=False, open_period='',
                                close_date='', is_closed=False, disable_notification=False, reply_to_message_id='',
                                reply_markup=''):
        tasks = []
        async with aiohttp.ClientSession() as session:
            for user in users:
                task = asyncio.create_task(self.send_poll(chat_id=user.tg_id,
                                                          question=question,
                                                          options=options,
                                                          type=type,
                                                          allows_multiple_answers=allows_multiple_answers,
                                                          correct_option_id=correct_option_id,
                                                          explanation=explanation,
                                                          explanation_parse_mode=explanation_parse_mode,
                                                          is_anonymous=is_anonymous,
                                                          open_period=open_period,
                                                          close_date=close_date,
                                                          is_closed=is_closed,
                                                          disable_notification=disable_notification,
                                                          reply_to_message_id=reply_to_message_id,
                                                          reply_markup=reply_markup))
                tasks.append(task)
            await asyncio.gather(*tasks)

    async def send_invoice(self, chat_id, title, description, payload, provider_token, start_parameter, currency,
                           prices, provider_data='', photo_url='', photo_size='', photo_width='', photo_height='',
                           need_name=False, need_phone_number=False, need_email=False, need_shipping_address=False,
                           send_phone_number_to_provider=False, send_email_to_provider=False, is_flexible=False,
                           disable_notification=False, reply_to_message_id='', reply_markup=''):
        method = 'sendInvoice?'
        params = {
            'chat_id': chat_id,
            'title': title,
            'description': description,
            'payload': payload,
            'provider_token': provider_token,
            'start_parameter': start_parameter,
            'currency': currency,
            'prices': prices,
            'provider_data': provider_data,
            'photo_url': photo_url,
            'photo_size': photo_size,
            'photo_width': photo_width,
            'photo_height': photo_height,
            'need_name': need_name,
            'need_phone_number': need_phone_number,
            'need_email': need_email,
            'need_shipping_address': need_shipping_address,
            'send_phone_number_to_provider': send_phone_number_to_provider,
            'send_email_to_provider': send_email_to_provider,
            'is_flexible': is_flexible,
            'disable_notification': disable_notification,
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': reply_markup
        }
        await self.__send_request(method, params)

    async def answer_pre_checkout_query(self, pre_checkout_query_id, ok, error_message):
        method = 'answerPreCheckoutQuery?'
        params = {
            'pre_checkout_query_id': pre_checkout_query_id,
            'ok': ok,
            'error_message': error_message
        }
        await self.__send_request(method, params)

    def set_webhook(self, url):
        method = 'setWebhook?'
        params = {
            'url': url
        }
        response = requests.get(self.url + method + urlencode(params))
        return response.json()

    def get_link(self, file_id):
        method = 'getFile?'
        params = {
            'file_id': file_id
        }
        response = requests.get(self.url + method + urlencode(params))
        try:
            local_file_path = response.json()['result']['file_path']
            global_file_path = f'https://api.telegram.org/file/bot{self.token}/{local_file_path}'
            return global_file_path
        except:
            return None

    async def get_file(self, file_id, path, ext):
        method = 'getFile?'
        params = {
            'file_id': file_id
        }
        response = requests.get(self.url + method + urlencode(params))
        local_file_path = response.json()['result']['file_path']
        global_file_path = f'https://api.telegram.org/file/bot{self.token}/{local_file_path}'
        file = requests.get(global_file_path)

        count = 0
        for f in os.listdir(path):
            if os.path.isfile(os.path.join(path, f)):
                count += 1

        with open(f'{path}{count+1}.{ext}', 'wb') as local_file:
            local_file.write(file.content)
            file_dir = os.path.dirname(local_file.name)
            file_path = f'./{file_dir}/{count+1}'
        return file_path

    def get_user_profile_photos(self, user_id):
        method = 'getUserProfilePhotos?'
        params = {
            'user_id': int(user_id),
            # 'offset': offset,
            # 'limit': limit
        }
        return requests.get(self.url + method + urlencode(params))