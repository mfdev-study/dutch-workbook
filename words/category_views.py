from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Category, CategorizedWord, Word


@login_required
def categories_list(request):
    categories = Category.objects.all()

    paginator = Paginator(categories, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "categories": categories,
        "page_obj": page_obj,
    }
    return render(request, "words/categories.html", context)


@login_required
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    categorized_words = CategorizedWord.objects.filter(category=category)
    words = [cw.word for cw in categorized_words]

    paginator = Paginator(words, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "category": category,
        "words": page_obj,
        "word_count": len(words),
    }
    return render(request, "words/category_detail.html", context)


@login_required
def create_category(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        color = request.POST.get("color", "#007bff").strip()

        if name:
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "color": color,
                },
            )

            if created:
                messages.success(request, f'Category "{name}" created successfully!')
            else:
                messages.info(request, f'Category "{name}" already exists.')

            return redirect("categories_list")

    return render(request, "words/create_category.html")


@login_required
def add_to_category(request, word_id):
    word = get_object_or_404(Word, id=word_id)
    categories = Category.objects.all()

    if request.method == "POST":
        category_id = request.POST.get("category")
        if category_id:
            category = get_object_or_404(Category, id=category_id)
            categorized_word, created = CategorizedWord.objects.get_or_create(
                word=word, category=category
            )

            if created:
                messages.success(request, f'"{word.dutch}" added to "{category.name}"')
            else:
                messages.info(
                    request, f'"{word.dutch}" is already in "{category.name}"'
                )

            return redirect("word_detail", word_id=word_id)

    # Get categories that this word is already in
    current_categories = Category.objects.filter(categorized_words__word=word)

    context = {
        "word": word,
        "categories": categories,
        "current_categories": current_categories,
    }
    return render(request, "words/add_to_category.html", context)


@login_required
def remove_from_category(request, word_id, category_id):
    word = get_object_or_404(Word, id=word_id)
    category = get_object_or_404(Category, id=category_id)

    CategorizedWord.objects.filter(word=word, category=category).delete()
    messages.success(request, f'"{word.dutch}" removed from "{category.name}"')

    return redirect("category_detail", category_id=category_id)


@login_required
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        color = request.POST.get("color", "#007bff").strip()

        if name and name != category.name:
            if Category.objects.filter(name=name).exists():
                messages.error(request, f'Category "{name}" already exists.')
            else:
                category.name = name

        category.description = description
        category.color = color
        category.save()

        messages.success(request, f'Category "{category.name}" updated successfully!')
        return redirect("categories_list")

    return render(request, "words/edit_category.html", {"category": category})


@login_required
def delete_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted successfully!')
        return redirect("categories_list")

    word_count = CategorizedWord.objects.filter(category=category).count()

    context = {
        "category": category,
        "word_count": word_count,
    }
    return render(request, "words/delete_category.html", context)
