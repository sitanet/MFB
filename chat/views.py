from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Max, Count
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from company.models import Branch
from accounts.models import User
from .models import ChatRoom, Message, MessageReadStatus
import json


@login_required(login_url='login')
def chat_home(request):
    """Main chat page showing all conversations"""
    user = request.user
    user_branch = user.branch
    user_company = user_branch.company if user_branch else None
    
    # Get all chat rooms the user is part of
    chat_rooms = ChatRoom.objects.filter(participants=user).annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count('messages', filter=Q(messages__is_read=False) & ~Q(messages__sender=user))
    ).order_by('-last_message_time')
    
    # Pre-process chat rooms to add other_participant for templates
    chat_rooms_list = []
    for room in chat_rooms:
        room.other_participant = room.get_other_participant(user)
        chat_rooms_list.append(room)
    
    # Get staff from same branch for starting new chats
    branch_staff = []
    company_staff = []
    
    if user_branch:
        branch_staff = User.objects.filter(
            branch_id=str(user_branch.id)
        ).exclude(id=user.id).exclude(role=13)  # Exclude customers
    
    if user_company:
        company_branch_ids = list(Branch.objects.filter(company=user_company).values_list('id', flat=True))
        company_branch_ids_str = [str(bid) for bid in company_branch_ids]
        company_staff = User.objects.filter(
            branch_id__in=company_branch_ids_str
        ).exclude(id=user.id).exclude(role=13)
    
    context = {
        'chat_rooms': chat_rooms_list,
        'branch_staff': branch_staff,
        'company_staff': company_staff,
    }
    return render(request, 'chat/chat_home.html', context)


@login_required(login_url='login')
def chat_room(request, room_uuid):
    """View a specific chat room"""
    user = request.user
    room = get_object_or_404(ChatRoom, uuid=room_uuid, participants=user)
    
    # Mark messages as read
    Message.objects.filter(room=room, is_read=False).exclude(sender=user).update(is_read=True)
    
    # Get messages with pagination
    messages = room.messages.select_related('sender').order_by('-created_at')[:50]
    messages = reversed(list(messages))
    
    # Get other participant for direct chats
    other_user = room.get_other_participant(user) if room.room_type == 'direct' else None
    
    context = {
        'room': room,
        'messages': messages,
        'other_user': other_user,
    }
    return render(request, 'chat/chat_room.html', context)


@login_required(login_url='login')
def start_chat(request, user_id):
    """Start or continue a direct chat with another user"""
    user = request.user
    other_user = get_object_or_404(User, id=user_id)
    
    # Check if they're in the same company
    user_branch = user.branch
    other_branch = other_user.branch
    
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not user_branch or not other_branch:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Invalid user'})
        return redirect('chat_home')
    
    user_company = user_branch.company
    other_company = other_branch.company
    
    if user_company != other_company:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'User not in same company'})
        return redirect('chat_home')
    
    # Find existing direct chat or create new one
    existing_room = ChatRoom.objects.filter(
        room_type='direct',
        participants=user
    ).filter(participants=other_user).first()
    
    if existing_room:
        if is_ajax:
            return JsonResponse({
                'success': True,
                'room_uuid': str(existing_room.uuid),
                'room_name': f"{other_user.first_name} {other_user.last_name}"
            })
        return redirect('chat_room', room_uuid=existing_room.uuid)
    
    # Create new chat room
    room = ChatRoom.objects.create(room_type='direct')
    room.participants.add(user, other_user)
    
    if is_ajax:
        return JsonResponse({
            'success': True,
            'room_uuid': str(room.uuid),
            'room_name': f"{other_user.first_name} {other_user.last_name}"
        })
    return redirect('chat_room', room_uuid=room.uuid)


@login_required(login_url='login')
@require_POST
def send_message(request):
    """Send a message via AJAX"""
    user = request.user
    
    try:
        data = json.loads(request.body)
        room_uuid = data.get('room_uuid')
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        room = get_object_or_404(ChatRoom, uuid=room_uuid, participants=user)
        
        message = Message.objects.create(
            room=room,
            sender=user,
            content=content
        )
        
        # Update room's updated_at
        room.save()
        
        return JsonResponse({
            'success': True,
            'message': {
                'uuid': str(message.uuid),
                'content': message.content,
                'sender_name': f"{user.first_name} {user.last_name}",
                'sender_id': user.id,
                'created_at': message.created_at.strftime('%H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='login')
def get_messages(request, room_uuid):
    """Get new messages for a room via AJAX polling"""
    user = request.user
    room = get_object_or_404(ChatRoom, uuid=room_uuid, participants=user)
    
    last_message_uuid = request.GET.get('last_message')
    
    if last_message_uuid:
        try:
            last_message = Message.objects.get(uuid=last_message_uuid)
            messages = room.messages.filter(created_at__gt=last_message.created_at)
        except Message.DoesNotExist:
            messages = room.messages.all()
    else:
        messages = room.messages.order_by('-created_at')[:50]
        messages = reversed(list(messages))
    
    # Mark as read
    Message.objects.filter(room=room, is_read=False).exclude(sender=user).update(is_read=True)
    
    messages_data = [{
        'uuid': str(m.uuid),
        'content': m.content,
        'sender_name': f"{m.sender.first_name} {m.sender.last_name}",
        'sender_id': m.sender.id,
        'is_own': m.sender.id == user.id,
        'created_at': m.created_at.strftime('%H:%M'),
    } for m in messages]
    
    return JsonResponse({'success': True, 'messages': messages_data})


@login_required(login_url='login')
def get_unread_count(request):
    """Get total unread message count for the user"""
    user = request.user
    
    unread_count = Message.objects.filter(
        room__participants=user,
        is_read=False
    ).exclude(sender=user).count()
    
    return JsonResponse({'unread_count': unread_count})


@login_required(login_url='login')
def search_staff(request):
    """Search for staff to start a chat"""
    user = request.user
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    user_branch = user.branch
    user_company = user_branch.company if user_branch else None
    
    if not user_company:
        return JsonResponse({'results': []})
    
    # Get company branch IDs
    company_branch_ids = list(Branch.objects.filter(company=user_company).values_list('id', flat=True))
    company_branch_ids_str = [str(bid) for bid in company_branch_ids]
    
    # Search staff
    staff = User.objects.filter(
        branch_id__in=company_branch_ids_str
    ).filter(
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(id=user.id).exclude(role=13)[:10]
    
    results = [{
        'id': s.id,
        'name': f"{s.first_name} {s.last_name}",
        'email': s.email,
        'branch': s.branch.branch_name if s.branch else 'Unknown',
        'role': s.get_role_display() if hasattr(s, 'get_role_display') else s.get_role(),
    } for s in staff]
    
    return JsonResponse({'results': results})
