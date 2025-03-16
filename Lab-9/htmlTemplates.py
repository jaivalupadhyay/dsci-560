css = '''
<style>
/* General Styling */
body {
    font-family: 'Arial', sans-serif;
    background-color: #fafafa;
    color: #333;
}

/* Chat Container */
.chat-message {
    display: flex;
    align-items: flex-start;
    padding: 10px;
    margin-bottom: 14px;
    border-radius: 18px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
}

/* User Message Styling */
.chat-message.user {
    background: linear-gradient(135deg, #6dd5ed 0%, #2193b0 100%);
    color: #ffffff;
    margin-left: auto;
    max-width: 70%;
    border-top-right-radius: 0;
}

/* Bot Message Styling */
.chat-message.bot {
    background: linear-gradient(135deg, #ffb88c 0%, #ff6f61 100%);
    color: #ffffff;
    margin-right: auto;
    max-width: 70%;
    border-top-left-radius: 0;
}

/* Avatar Styling */
.chat-message .avatar {
    width: 50px;
    height: 50px;
    margin-right: 12px;
    flex-shrink: 0;
}

/* Rounded Avatar for Bot */
.chat-message.bot .avatar img {
    border-radius: 15%;
    object-fit: cover;
    width: 100%;
    height: 100%;
}

/* Circle Avatar for User */
.chat-message.user .avatar img {
    border-radius: 50%;
    object-fit: cover;
    width: 100%;
    height: 100%;
}

/* Message Text */
.chat-message .message {
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 15px;
    line-height: 1.4;
}

/* Hover Effect */
.chat-message:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0,0,0,0.15);
}
</style>
'''

# Bot Message Template
bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://upload.wikimedia.org/wikipedia/commons/0/0c/Chatbot_img.png">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

# User Message Template
user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''
