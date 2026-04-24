import uuid
from django.conf import settings
from django.utils import timezone
from ..models import UserCourse, Course, User

class YookassaPayment:
    """данный класс описывает логику интеграции системы с Юкассой для оплаты курсов"""
    
    def __init__(self):
        from yookassa import Configuration
        
        shop_id = str(settings.YOOKASSA_SHOP_ID).strip()
        secret_key = str(settings.YOOKASSA_SECRET_KEY).strip()
        secret_key = secret_key.strip('"').strip("'")
        
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key
    
    def create_payment(self, course, user, return_url):
        from yookassa import Payment
        
        payment = Payment.create({
            "amount": {
                "value": str(course.course_price),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": f"Оплата курса: {course.course_name}",
            "metadata": {
                "course_id": course.id,
                "user_id": user.id,
                "course_name": course.course_name
            }
        }, str(uuid.uuid4()))
        
        return payment
    
    def check_payment_status(self, payment_id):
        from yookassa import Payment
        payment_info = Payment.find_one(payment_id)
        return payment_info.status
    
    def process_successful_payment(self, payment_id):
        from yookassa import Payment
        
        payment_info = Payment.find_one(payment_id)
        
        if payment_info.status == 'succeeded':
            course_id = payment_info.metadata.get('course_id')
            user_id = payment_info.metadata.get('user_id')
            
            course = Course.objects.get(id=course_id)
            user = User.objects.get(id=user_id)
            
            user_course, created = UserCourse.objects.get_or_create(
                user=user,
                course=course,
                defaults={
                    'course_price': course.course_price,
                    'payment_date': timezone.now(),
                    'payment_id': payment_id,
                    'status_course': False,
                    'is_active': True
                }
            )
            
            if not created and not user_course.is_active:
                user_course.is_active = True
                user_course.payment_date = timezone.now()
                user_course.payment_id = payment_id
                user_course.save()
            
            return True, user_course
        
        return False, None