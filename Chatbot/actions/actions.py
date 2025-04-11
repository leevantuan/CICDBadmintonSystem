from typing import Any, Text, Dict, List, Tuple, Optional
from rasa_sdk import Action, Tracker, executor
from rasa_sdk.events import SlotSet
from rasa_sdk.events import UserUtteranceReverted
from utils.quantity_processcor import process_quantity
from urllib.parse import quote
from datetime import datetime, timedelta

import re
import requests

url = "https://bookingweb.shop/api/v1"

# =========================== ACTION GET TOP CLUBS ====================================

class ActionFetchTopClubs(Action):
    def name(self) -> Text:
        return "action_fetch_top_clubs"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        try:
            quantity = self._process_quantity(tracker)
            clubs = self._fetch_clubs(quantity)
            response = self._generate_response(clubs, quantity)
            dispatcher.utter_message(text=response)
            return [SlotSet("quantity", str(quantity))]
        
        except Exception:
            dispatcher.utter_message(text="Xin lỗi, có lỗi khi tìm club. Vui lòng thử lại.")
            return []

    def _process_quantity(self, tracker: Tracker) -> int:
        """Validate và chuẩn hóa quantity"""
        quantity = int(process_quantity(
            tracker.latest_message.get('text', ''),
            next(tracker.get_latest_entity_values("quantity"), None)))

        return max(1, min(5, int(quantity or 3)))

    def _fetch_clubs(self, quantity: int) -> List[Dict]:
        """Lấy danh sách club từ API (chỉ lấy name, rating, hotline)"""
        try:
            response = requests.get(
                f"https://bookingweb.shop/api/v1/clubs/top-club/{quantity}",
                timeout=5
            )
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess", False):
                raise ValueError("API returned unsuccessful status")

            return [
                {
                    "name": club.get("name", "Unknown Club"),
                    "rating": float(club.get("averageRating", 0)),
                    "hotline": club.get("hotline", "N/A")
                }
                for club in api_data.get("value", [])
            ]

        except Exception as e:
            return []

    def _generate_response(self, clubs: List[Dict], quantity: int) -> str:
        """Tạo message chỉ hiển thị name, rating, hotline"""
        response = f"🏆 Top {quantity} club:\n"
        for idx, club in enumerate(clubs, 1):
            response += f"{idx}. {club['name']} (⭐️{club['rating']}) 📞{club['hotline']}\n"
        return response

# =========================== ACTION FREE TIMES ====================================

class ActionCheckYardAvailability(Action):
    def name(self) -> Text:
        return "action_check_yard_availability"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        yard_name = next(tracker.get_latest_entity_values("yardName"), tracker.get_slot("yardName"))
        start_time = next(tracker.get_latest_entity_values("check_startTime"), tracker.get_slot("check_startTime") or "00:00")
        end_time = next(tracker.get_latest_entity_values("check_endTime"), tracker.get_slot("check_endTime")  or "22:00")
        days_ahead = int(next(tracker.get_latest_entity_values("quantityDate"), tracker.get_slot("quantityDate")))
        
        # yard_name = tracker.get_slot("yardName")
        # days_ahead = int(tracker.get_slot("quantityDate"))
        # start_time = tracker.get_slot("check_startTime") or "00:00"
        # end_time = tracker.get_slot("check_endTime") or "22:00"
        
        print(f"club name: {yard_name}, start time: {start_time}, end time: {end_time}, date: {days_ahead}")
        
        if not yard_name:
            dispatcher.utter_message(text="Vui lòng cung cấp tên sân cầu lông.")
            return []

        # Handle Data input
        response = self._fetch_free_times(days_ahead,start_time,end_time,yard_name)
        
        dispatcher.utter_message(text=response)
        
        return []
    def extract_time_range(self,time_slot: str) -> Tuple[Optional[str], Optional[str]]:

        time_slot = time_slot.strip()
        
        pattern = r"(\d{1,2}:\d{2})\s*(?:đến|tới|-)\s*(\d{1,2}:\d{2})"
        match = re.search(pattern, time_slot)

        if match:
            start_time = match.group(1)
            end_time = match.group(2)
            return start_time, end_time
        else:
            return None, None
        
    # GET API FREE TIME
    def format_time(self, s: str) -> str:
        return s[:2] + ":00" if len(s) >= 2 else "00:00"

    def _fetch_free_times(self, date: int,startTime:str,endTime:str,yardName:str) -> str:
        """Lấy free times"""
        try:
            time_now = "00:00"

            # Handler date format and time now format
            if date == 0:
                target_date = datetime.now().strftime("%Y-%m-%d")  # Format: 2025-03-27
                time_now = datetime.now().strftime("%H:%M")
            else:
                target_date = (datetime.now() + timedelta(days=date)).strftime("%Y-%m-%d")
            
            # Handler tenant Code
            tenant_code = self._fetch_code_clubs(yardName)
            if not tenant_code:
                raise ValueError("Rất xin lỗi! Vui lòng kiểm tra lại tên câu lạc bộ!")
            
            params = {
                "date": target_date,
                "startTime": startTime,
                "endTime": endTime,
                "tenant": tenant_code,
                "timeNow": time_now
            }
            
            response = requests.get(
                f"{url}/yard-prices/filter-by-date/free-yard?",
                params=params,
                timeout=5
            )
            
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess") or not api_data.get("value"):
                raise ValueError("Rất xin lỗi! Hệ thống đang gặp sự cố vui lòng kiểm tra lại!")
            
            # Tạo response text
            response_text = self._format_response(api_data["value"], yardName)
            
            return response_text
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    # Format response
    def _format_response(self, time_slots: List[Dict], yard_name: str) -> str:
        """Chuyển đổi dữ liệu API thành text format"""
        result = [f"Các khung giờ còn trống của {yard_name}:\n"]
        
        for slot in time_slots:
            # Format thời gian (bỏ giây)
            start = slot["startTime"][:5]
            end = slot["endTime"][:5]
            
            # Sắp xếp và format danh sách sân
            yards = sorted(slot["yardNames"])
            yards_text = ", ".join([f"sân {y}" for y in yards])
            result.append(f"⏰ Khung giờ: {start} - {end} \n- Còn trống: {yards_text}")
        
        return "\n".join(result)
    
    # GET API CODE CLUBS
    def _fetch_code_clubs(self, yardName: str) -> str:
        """Lấy Code Club"""
        try:
            encoded_name = quote(yardName)
            
            response = requests.get(
                f"{url}/clubs/get-code/{encoded_name}",
                timeout=5
            )
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess", False):
                raise ValueError("API returned unsuccessful status")

            return api_data.get("value", {}).get("code", "")

        except Exception as e:
            return []
 
# =========================== ACTION INFO CLUB ====================================

class ActionProvideClubInfo(Action):
    def name(self) -> Text:
        return "action_provide_club_info"

    def run(self, dispatcher: executor.CollectingDispatcher, tracker: Tracker, domain: Dict):
        club_name = tracker.get_slot("club_name")
        
        response = self._fetch_info_club(club_name)
        
        dispatcher.utter_message(text=response)
        
        return []
    
    # Call API
    def _fetch_info_club(self, clubName: str) -> str:
        """Lấy Info Club"""
        try:
            encoded_name = quote(clubName)
            
            response = requests.get(
                f"{url}/tenants/get-by-tenant-name/{encoded_name}",
                timeout=5
            )
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess", False):
                raise ValueError("API returned unsuccessful status")

            club_info = api_data.get("value", {})
        
            if not club_info:
                return "Không tìm thấy thông tin club! Vui lòng kiểm tra lại."
                
            # Format information for clubs
            return (
                f"Thông tin {club_info.get('name', '')}:\n"
                f"📞 Hotline: {club_info.get('hotLine', 'Chưa cập nhật')}\n"
                f"📍 Địa chỉ: {club_info.get('address', '')}, {club_info.get('city', '')}\n"
                f"✉️  Email: {club_info.get('email', 'Chưa cập nhật')}\n"
                f"📢 Slogan: {club_info.get('slogan', '')}\n"
            )

        except Exception as e:
            return []
    # Format response
   
# =========================== ACTION Confirm ====================================

class ActionConfirmBooking(Action):
    def name(self) -> Text:
        return "action_confirm_booking"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        club_name = tracker.get_slot("book_clubName")
        booking_date = int(tracker.get_slot("book_date"))
        time_slot = tracker.get_slot("book_timeSlot")
        
        start_time, end_time = self.extract_time_range(time_slot)
        
        # print(f"club name: {club_name}, start time: {start_time}, end time: {end_time}, date: {booking_date}")

        message = self._fetch_check_free_times(booking_date,start_time,end_time,club_name);
        dispatcher.utter_message(text=message)

        return []

    def extract_time_range(self,time_slot: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Tách startTime và endTime từ book_timeSlot (VD: '18:00 đến 20:00', '14:00 - 16:00', '10:00 tới 12:00')
        """
        time_slot = time_slot.strip()
        
        pattern = r"(\d{1,2}:\d{2})\s*(?:đến|tới|-)\s*(\d{1,2}:\d{2})"
        match = re.search(pattern, time_slot)

        if match:
            start_time = match.group(1)
            end_time = match.group(2)
            return start_time, end_time
        else:
            return None, None
    
    def format_time(self, s: str) -> str:
        return s[:2] + ":00" if len(s) >= 2 else "00:00"
    
    # Check free time
    def _fetch_check_free_times(self, date: int,startTime:str,endTime:str,yardName:str) -> str:
        """Lấy free times"""
        try:
            # Handler date format and time now format
            if date == 0:
                target_date = datetime.now().strftime("%Y-%m-%d")  # Format: 2025-03-27
            else:
                target_date = (datetime.now() + timedelta(days=date)).strftime("%Y-%m-%d")
            
            # Handler tenant Code
            tenant_code = self._fetch_code_clubs(yardName)

            # if len(startTime) >= 3 and startTime[2] == "h":
            #     startTime = self.format_time(startTime)
                
            # if len(endTime) >= 3 and endTime[2] == "h":
            #     endTime = self.format_time(endTime)
            
            params = {
                "date": target_date,
                "startTime": startTime,
                "endTime": endTime,
                "tenant": tenant_code,
            }
            
            response = requests.get(
                f"{url}/bookings/check-unbooked?",
                params=params,
                timeout=30
            )
            
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess") or not api_data.get("value"):
                raise ValueError("Rất xin lỗi! Thời gian bạn chọn không còn sân trống. Vui lòng kiểm tra lại!")
            
            # Tạo response text
            response_text = self._format_response(api_data["value"], yardName)
            
            return response_text
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _format_response(self, value_data, yardName):
        if not value_data:
            return "❌ Hiện tại chưa có khung giờ nào khả dụng để đặt sân."

        time_slots = []
        for item in value_data:
            start = item.get("startTime", "??:??")
            end = item.get("endTime", "??:??")
            time_slots.append(f"{start} đến {end}")

        time_slots_str = ", ".join(time_slots)

        response_text = (
            f"✅ Hãy nhập email của bạn để đặt sân tại {yardName} vào các khung giờ sau: {time_slots_str} nhé!"
        )

        return response_text


     # GET API CODE CLUBS
    
    def _fetch_code_clubs(self, yardName: str) -> str:
        """Lấy Code Club"""
        try:
            encoded_name = quote(yardName)
            
            response = requests.get(
                f"{url}/clubs/get-code/{encoded_name}",
                timeout=5
            )
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess", False):
                raise ValueError("API returned unsuccessful status")

            return api_data.get("value", {}).get("code", "")

        except Exception as e:
            return []
 
# =========================== ACTION Create ====================================

class ActionCreateBooking(Action):
    def name(self) -> Text:
        return "action_create_booking"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        email = tracker.get_slot("book_email")
        club_name = tracker.get_slot("book_clubName")
        booking_date = int(tracker.get_slot("book_date"))
        time_slot = tracker.get_slot("book_timeSlot")
        
        start_time, end_time = self.extract_time_range(time_slot)
        
        print(f"club name: {club_name}, start time: {start_time}, end time: {end_time}, date: {booking_date},email: {email} ")

        message = self._fetch_create_times(booking_date,start_time,end_time,club_name,email);
        dispatcher.utter_message(text=message)

        return []
    
    def extract_time_range(self,time_slot: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Tách startTime và endTime từ book_timeSlot (VD: '18:00 đến 20:00', '14:00 - 16:00', '10:00 tới 12:00')
        """
        time_slot = time_slot.strip()
        
        pattern = r"(\d{1,2}:\d{2})\s*(?:đến|tới|-)\s*(\d{1,2}:\d{2})"
        match = re.search(pattern, time_slot)

        if match:
            start_time = match.group(1)
            end_time = match.group(2)
            return start_time, end_time
        else:
            return None, None
        
    def format_time(self, s: str) -> str:
        return s[:2] + ":00" if len(s) >= 2 else "00:00"
    
    # Check free time
    def _fetch_create_times(self, date: int,startTime:str,endTime:str,yardName:str, email:str) -> str:
        """Lấy free times"""
        try:
            # Handler date format and time now format
            if date == 0:
                target_date = datetime.now().strftime("%Y-%m-%d")  # Format: 2025-03-27
            else:
                target_date = (datetime.now() + timedelta(days=date)).strftime("%Y-%m-%d")
            
            # Handler tenant Code
            tenant_code = self._fetch_code_clubs(yardName)
            # startTime = self.format_time(startTime)
            # endTime = self.format_time(endTime)
            
            params = {
                "date": target_date,
                "startTime": startTime,
                "endTime": endTime,
                "tenantCode": tenant_code,
                "email": email,
            }
            
            response = requests.get(
                f"{url}/bookings/create-booking-by-chat?",
                params=params,
                timeout=30
            )
            
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess") or not api_data.get("value"):
                raise ValueError("Rất xin lỗi! Thời gian bạn chọn không còn sân trống. Vui lòng kiểm tra lại!")
            
            # Tạo response text
            response_text = self._format_response(api_data["value"])
            
            return response_text
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _format_response(self, value_data):
        if not value_data:
            return "No payment information available"
        
        # Get the payment URL
        pay_url = value_data.get("payUrl", "")
        
        if not pay_url:
            return "Vui lòng thanh toán qua QRCode. Url thanh toán không khả dụng"
        
        # Return your message with the payment URL appended
        return f"Vui lòng thanh toán qua QRCode. Url = {pay_url}"

     # GET API CODE CLUBS
    def _fetch_code_clubs(self, yardName: str) -> str:
        """Lấy Code Club"""
        try:
            encoded_name = quote(yardName)
            
            response = requests.get(
                f"{url}/clubs/get-code/{encoded_name}",
                timeout=5
            )
            response.raise_for_status()

            api_data = response.json()

            if not api_data.get("isSuccess", False):
                raise ValueError("API returned unsuccessful status")

            return api_data.get("value", {}).get("code", "")

        except Exception as e:
            return []
 
# =========================== ACTION Fall Back ====================================

class ActionFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(response="utter_default")

        return [UserUtteranceReverted()]
    
# =========================== ACTION Check booking ====================================

class ActionCheckBooking(Action):
    def name(self) -> Text:
        return "action_check_booking"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        date = int(tracker.get_slot("check_date"))
        
        if date is None:
            dispatcher.utter_message(text="Vui lòng cung cấp thời gian chính xác.")
            return []

        if date == 0:
            target_date = datetime.now().strftime("%d-%m-%Y")  # Format: 2025-03-27
        else:
            target_date = (datetime.now() + timedelta(days=date)).strftime("%Y-%m-%d")
            
        dispatcher.utter_message(text=f"Vui lòng nhập Email cần kiểm tra lịch cho ngày {target_date}")

        return []


class ActionHandleCheckBooking(Action):
    def name(self) -> Text:
        return "action_handle_booking"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        date = int(tracker.get_slot("check_date"))
        email = tracker.get_slot("email")
        
        message = self._fetch_check_booking(date,email);
        dispatcher.utter_message(text=message)
        
        return []
    
        
    # Check free time
    def _fetch_check_booking(self, date: int, email:str) -> str:
        """Lấy free times"""
        try:
            # Handler date format and time now format
            if date == 0:
                target_date = datetime.now().strftime("%Y-%m-%d")  # Format: 2025-03-27
            else:
                target_date = (datetime.now() + timedelta(days=date)).strftime("%Y-%m-%d")
            
            params = {
                "date": target_date,
                "email": email,
            }
            
            response = requests.get(
                f"{url}/booking-histories/get-by-date?",
                params=params,
                timeout=30
            )
            
            # response = requests.get(
            #     f"{url}/bookings/create-booking-by-chat?",
            #     params=params,
            #     timeout=30
            # )
            
            response.raise_for_status()
            api_data = response.json()

            if not api_data.get("isSuccess") or not api_data.get("value"):
                raise ValueError("Rất xin lỗi thông tin không chính xác! Vui lòng kiểm tra lại!")
            
            # Tạo response text
            response_text = self._format_response(api_data["value"])
            
            return response_text
        
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _format_response(self, bookings: list) -> str:
        responses = []

        for booking in bookings:
            club_name = booking.get("clubName", "không rõ sân")
            start_time = booking.get("startTime", "không rõ thời gian")

            response = f"Hôm nay bạn có lịch tại sân {club_name} lúc {start_time}"
            responses.append(response)

        return "\n".join(responses)