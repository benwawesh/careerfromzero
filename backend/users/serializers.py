from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class ProfilePictureValidator:
    """Validator for profile picture uploads"""
    
    ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    ALLOWED_MIME_TYPES = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp',
    ]
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MIN_FILE_SIZE = 10 * 1024  # 10KB
    
    @classmethod
    def validate(cls, value):
        """Validate profile picture"""
        if not value:
            return value
        
        # Check if it's an uploaded file
        if not isinstance(value, InMemoryUploadedFile):
            raise serializers.ValidationError("Invalid file type")
        
        # Check file size
        if value.size > cls.MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size exceeds maximum limit of {cls.MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        if value.size < cls.MIN_FILE_SIZE:
            raise serializers.ValidationError(
                f"File size is too small. Minimum size is {cls.MIN_FILE_SIZE // 1024}KB"
            )
        
        # Check file extension
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in cls.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(cls.ALLOWED_EXTENSIONS)}"
            )
        
        # Check MIME type
        if value.content_type not in cls.ALLOWED_MIME_TYPES:
            raise serializers.ValidationError(
                f"Invalid image format. Allowed formats: JPEG, PNG, GIF, WebP"
            )
        
        logger.info(f"Profile picture validated: {value.name} ({value.size} bytes)")
        return value


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name',
            'password', 'password2', 'phone_number', 'bio', 'location',
            'linkedin_url', 'github_url', 'portfolio_url', 'job_search_preferences',
            'career_goals', 'profile_picture'
        )
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        # username is auto-generated in User.save() from the email prefix
        user = User.objects.create_user(**validated_data)

        # Give free trial tokens to new user
        try:
            from payments.token_service import add_credits
            from decouple import config
            free_credits = int(config('FREE_TRIAL_CREDITS', default=50))
            if free_credits > 0:
                add_credits(user, free_credits, 'Free trial credits', transaction_type='bonus')
        except Exception:
            pass  # Don't block registration if token grant fails

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(validators=[ProfilePictureValidator.validate], required=False)
    
    class Meta:
        model = User
        fields = (
            'first_name', 'last_name', 'phone_number', 'bio', 'location',
            'linkedin_url', 'github_url', 'portfolio_url', 'job_search_preferences',
            'career_goals', 'profile_picture'
        )


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'bio', 'location', 'linkedin_url', 'github_url',
            'portfolio_url', 'job_search_preferences', 'career_goals',
            'profile_picture', 'created_at', 'updated_at', 'is_staff', 'is_superuser'
        )
        read_only_fields = ('id', 'username', 'email', 'created_at', 'updated_at')


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin to manage user details"""
    class Meta:
        model = User
        fields = '__all__'
        read_only_fields = ('id', 'username', 'created_at', 'updated_at')
