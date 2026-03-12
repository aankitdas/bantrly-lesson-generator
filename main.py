from src.core.generator import LessonGenerator


def main():
    print("\nBantrly Lesson Generator")
    print("=" * 40)

    grade_band = input("Grade Band (K-2 / 3-5 / 6-8 / 9-12)     : ").strip()
    ela_domain = input("ELA Domain (Speaking / Listening / Reading / Writing / Reading → Speaking): ").strip()
    theme      = input("Theme (e.g. Space Exploration)             : ").strip()

    gen = LessonGenerator(verbose=True)
    lesson = gen.generate(
        grade_band=grade_band,
        ela_domain=ela_domain,
        theme=theme
    )

    print(f"\nLesson saved to: data/generated/{lesson['lesson_id']}.json")


if __name__ == "__main__":
    main()