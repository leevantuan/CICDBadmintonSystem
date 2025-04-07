from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, executor
from rasa_sdk.events import SlotSet
from utils.quantity_processcor import process_quantity
from urllib.parse import quote
from datetime import datetime, timedelta

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
        quantity = tracker.get_slot("quantity") or process_quantity(
            tracker.latest_message.get('text', ''),
            next(tracker.get_latest_entity_values("quantity"), None))

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
        
        # Xử lý các entity với giá trị mặc định
        yard_name = next(tracker.get_latest_entity_values("yardName"), tracker.get_slot("yardName"))
        start_time = next(tracker.get_latest_entity_values("startTime"), tracker.get_slot("startTime") or "05:00")
        end_time = next(tracker.get_latest_entity_values("endTime"), tracker.get_slot("endTime") or "22:00")
        days_ahead = int(next(tracker.get_latest_entity_values("quantityDate"), tracker.get_slot("quantityDate") or "0"))

        # Kiểm tra bắt buộc có yardName
        if not yard_name:
            dispatcher.utter_message(text="Vui lòng cung cấp tên sân cầu lông.")
            return []

        # Handle Data input
        response = self._fetch_free_times(days_ahead,start_time,end_time,yard_name)
        
        dispatcher.utter_message(text=response)
        
        return []

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
            startTime = self.format_time(startTime)
            endTime = self.format_time(endTime)
            
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
   
# =========================== ACTION Fall Back ====================================

class ActionConfirmBooking(Action):
    def name(self) -> Text:
        return "action_confirm_booking"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        club_name = tracker.get_slot("book_clubName")
        start_time = tracker.get_slot("book_startTime")
        end_time = tracker.get_slot("book_endTime")
        booking_date = tracker.get_slot("book_date")

        message = f"✅ Hãy nhập email của bạn để đặt sân tại {club_name} từ {start_time} đến {end_time} vào {booking_date} nhé!"
        dispatcher.utter_message(text=message)

        return []


class ActionCreateBooking(Action):
    def name(self) -> Text:
        return "action_create_booking"

    def run(self, dispatcher: executor.CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        email = tracker.get_slot("email")
        club_name = tracker.get_slot("book_clubName")
        start_time = tracker.get_slot("book_startTime")
        end_time = tracker.get_slot("book_endTime")
        booking_date = tracker.get_slot("book_date")

        message = f"✅ Hãy nhập email: {email} của bạn để đặt sân tại {club_name} từ {start_time} đến {end_time} vào {booking_date} nhé!"
        dispatcher.utter_message(text=message)

        return []