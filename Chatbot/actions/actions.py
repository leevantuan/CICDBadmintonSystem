from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, executor
from rasa_sdk.events import SlotSet
from utils.quantity_processcor import process_quantity
from urllib.parse import quote

import requests

url = "https://bookingweb.shop/api/v1"

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


# ===============================================================

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

        yard_code = self._fetch_code_clubs(yard_name)
        # try:
        #     # Gọi API kiểm tra sân trống
        #     # availability = self._check_availability_api(
        #     #     yard_name,
        #     #     start_time,
        #     #     end_time,
        #     #     int(days_ahead)
        #     # )

        #     isYardName = self._check_availability_api(
        #         yard_name
        #     )

        #     # if isYardName.get("is_available", False):
        #     if isYardName:
        #         dispatcher.utter_message(text=f"Sân {yard_name} còn trống từ {start_time} đến {end_time}!")
        #     else:
        #         dispatcher.utter_message(text=f"Hiện sân {yard_name} không còn trống trong khoảng thời gian này.")

        # except Exception as e:
        #     # dispatcher.utter_message(text="Xin lỗi, hiện không thể kiểm tra sân. Vui lòng thử lại sau.")
        #     dispatcher.utter_message(text=f"Vui lòng cung cấp tên sân cầu lông.{yard_name}{start_time}{end_time}{days_ahead}")
            
        dispatcher.utter_message(text=f"Vui lòng cung cấp tên sân cầu lông. Code: {yard_code}")
        
        return []

    def _fetch_code_clubs(self, yardName: str) -> List[Dict]:
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

            return api_data.get("value", [])

        except Exception as e:
            return []
        
        

    # def _get_fallback_clubs(self, quantity: int) -> List[Dict]:
    #     """Dữ liệu dự phòng đơn giản"""
    #     return [
    #                {"name": "The Champion", "rating": 4.9, "hotline": "0232921582"},
    #                {"name": "Smash Arena", "rating": 4.8, "hotline": "032921582"}
    #            ][:quantity]

    # def _fetch_clubs(self, quantity: int) -> List[Dict]:
    #     """Lấy danh sách club (mock data)"""
    #     return [
    #         {"name": "The Champion", "rating": 4.9},
    #         {"name": "Smash Arena", "rating": 4.8},
    #         {"name": "Net King", "rating": 4.7},
    #         {"name": "Racket Pro", "rating": 4.6},
    #         {"name": "Shuttle Master", "rating": 4.5}
    #     ][:quantity]

    # def _generate_response(self, clubs: List[Dict], quantity: int) -> str:
    #     """Tạo message response"""
    #     return (
    #         f"🏆 Top {quantity} club:\n" +
    #         "\n".join(f"{i}. {c['name']} (⭐️{c['rating']})"
    #                  for i, c in enumerate(clubs, 1)) +
    #         ("\nBạn muốn đặt sân ở đây không?" if quantity == 1 else "")
    #     )